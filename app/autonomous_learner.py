"""
Aprendizaje autónomo: el agente busca información relevante en internet
y la guarda en su RAG sin necesidad de que el usuario lo pida.

Ciclo:
  1. Cada N horas elige un topic de su matriz de interés
  2. Busca en DuckDuckGo → obtiene URLs relevantes
  3. Fetches el contenido de las mejores URLs
  4. Extrae el texto útil y lo guarda en ChromaDB
  5. Registra lo que aprendió en un log
"""
import threading, time, re, hashlib, os, json, csv, io
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

_LOG_PATH = Path(__file__).parent.parent / "data" / "learner_log.jsonl"
_STOP_EVENT   = threading.Event()
_LEARNER_LOCK = threading.Lock()
_STATE_LOCK   = threading.Lock()
_LOG_LOCK     = threading.Lock()

# Matriz de interés: (query, tags, plataforma, intervalo_horas)
# El agente rota por estas áreas de conocimiento priorizando las más desactualizadas
INTEREST_MATRIX = [
    # Ciberseguridad — alta prioridad
    ("new CVE vulnerabilities 2025 critical Windows Linux",          ["security", "cve"],      "all",     12),
    ("NVD critical CVE Windows Linux network remote code execution",  ["security", "cve", "nvd"], "all",   12),
    ("CISA KEV known exploited vulnerabilities ransomware edge devices", ["security", "kev", "threat-intel"], "all", 12),
    ("Exploit-DB recent remote code execution privilege escalation",  ["security", "exploit-db", "exploit"], "all", 24),
    ("advanced PowerShell offensive security techniques 2025",       ["security", "powershell"],"windows", 24),
    ("privilege escalation Linux techniques 2025",                   ["security", "linux"],     "linux",   24),
    ("malware analysis techniques evasion 2025",                     ["security", "malware"],   "all",     48),
    ("MITRE ATT&CK threat intelligence techniques detection 2025",    ["security", "threat-intel", "mitre"], "all", 48),
    ("web application hacking OWASP top 10 2025",                   ["security", "web"],       "all",     48),
    # IA y agentes — media prioridad
    ("Ollama local LLM new models performance 2025",                 ["ai", "ollama"],          "all",     24),
    ("AI agent autonomous tools function calling 2025",              ["ai", "agent"],           "all",     24),
    ("Qwen2.5 vs DeepSeek model comparison benchmark 2025",         ["ai", "models"],          "all",     48),
    # Python y automatización
    ("Python system automation new libraries 2025",                  ["python", "automation"],  "all",     48),
    ("Python async concurrent performance tips",                     ["python"],                "all",     72),
    # Windows y Linux admin
    ("Windows 11 administration PowerShell tips advanced",           ["windows", "admin"],      "windows", 48),
    ("Linux kernel security hardening guide 2025",                   ["linux", "security"],     "linux",   72),
    # Red e infraestructura
    ("network penetration testing tools techniques 2025",            ["network", "security"],   "all",     48),
    ("Docker Kubernetes security best practices 2025",               ["docker", "containers"],  "all",     72),
]

_STATE_FILE = Path(__file__).parent.parent / "data" / "learner_state.json"
_NVD_CVES_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
_EXPLOITDB_CSV_URL = "https://gitlab.com/exploit-database/exploitdb/-/raw/main/files_exploits.csv"
_SOURCE_WEIGHTS = {
    "nvd.nist.gov": 7,
    "services.nvd.nist.gov": 7,
    "cisa.gov": 7,
    "mitre.org": 6,
    "attack.mitre.org": 6,
    "exploit-db.com": 5,
    "gitlab.com": 4,
    "owasp.org": 4,
    "github.com": 2,
}


def _load_state() -> dict:
    """Carga cuándo se buscó por última vez cada topic."""
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: dict):
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = _STATE_FILE.with_suffix(".tmp")
    with _STATE_LOCK:
        tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp.replace(_STATE_FILE)


def _next_topic(state: dict):
    """Elige el topic más prioritario (el más desactualizado según su intervalo)."""
    now = time.time()
    best = None
    best_overdue = -1
    for i, (query, tags, platform, interval_h) in enumerate(INTEREST_MATRIX):
        last = state.get(str(i), 0)
        overdue = (now - last) / (interval_h * 3600)
        if overdue > best_overdue:
            best_overdue = overdue
            best = i
    return best, best_overdue >= 1.0  # (index, should_run_now)


def _is_safe_url(url: str) -> bool:
    try:
        from urllib.parse import urlparse
        import ipaddress
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False
        host = p.hostname or ""
        try:
            ip = ipaddress.ip_address(host)
            return ip.is_global
        except ValueError:
            pass  # es un hostname, no una IP
        return host not in ("localhost", "127.0.0.1", "::1") and not host.endswith(".local")
    except Exception:
        return False


def _fetch_url(url: str, timeout: int = 12) -> str:
    """Descarga y limpia el texto de una URL."""
    if not _is_safe_url(url):
        return ""
    try:
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CyberAgent-Learner/1.0)",
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        }
        r = httpx.get(url, headers=headers, timeout=timeout, follow_redirects=True)
        html = r.text
        # Eliminar scripts, styles y tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>',  '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<[^>]+>', ' ', html)
        # Limpiar espacios
        text = re.sub(r'\s+', ' ', html).strip()
        return text[:6000]  # máximo 6k chars por página
    except Exception:
        return ""


def _web_search_raw(query: str, max_results: int = 4) -> list[dict]:
    """Busca en DuckDuckGo y devuelve resultados."""
    try:
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        }
        r = httpx.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers=headers,
            timeout=20,
            follow_redirects=True,
        )
        html = r.text
        def clean(s): return re.sub(r'<[^>]+>', '', s).strip()

        titles   = [clean(m) for m in re.findall(r'class="result__a"[^>]*>(.*?)</a>', html, re.DOTALL)]
        snippets = [clean(m) for m in re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.DOTALL)]
        # Extract actual href URLs from result links
        hrefs = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"', html)
        # DuckDuckGo wraps in /l/?uddg= redirect — decode
        decoded_urls = []
        for h in hrefs:
            m = re.search(r'uddg=([^&]+)', h)
            if m:
                from urllib.parse import unquote
                decoded_urls.append(unquote(m.group(1)))
            elif h.startswith("http"):
                decoded_urls.append(h)

        results = []
        for i in range(min(max_results, len(titles))):
            results.append({
                "title":   titles[i],
                "snippet": snippets[i] if i < len(snippets) else "",
                "url":     decoded_urls[i] if i < len(decoded_urls) else "",
            })
        return results
    except Exception:
        return []


def _host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _source_score(url: str, tags: list[str]) -> int:
    host = _host(url)
    score = 0
    for domain, weight in _SOURCE_WEIGHTS.items():
        if host == domain or host.endswith("." + domain):
            score += weight
            break
    if "cve" in tags and ("nvd.nist.gov" in host or "cve.org" in host):
        score += 4
    if "threat-intel" in tags and any(x in host for x in ("cisa.gov", "mitre.org")):
        score += 4
    if "exploit-db" in tags and any(x in host for x in ("exploit-db.com", "gitlab.com")):
        score += 4
    return score


def _rank_results(results: list[dict], tags: list[str], limit: int = 6) -> list[dict]:
    seen = set()
    ranked = []
    for item in results:
        title = (item.get("title") or "").strip()
        url = (item.get("url") or "").strip()
        key = (url or title).lower()
        if not key or key in seen:
            continue
        seen.add(key)
        content_len = len(item.get("content") or item.get("snippet") or "")
        ranked.append((_source_score(url, tags), content_len, item))
    ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [item for _, _, item in ranked[:limit]]


def _nvd_recent_cves(query: str, max_results: int = 5) -> list[dict]:
    """Fetch recent high-signal CVEs from the NVD 2.0 CVE API."""
    try:
        import httpx
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=21)
        params = {
            "keywordSearch": " ".join(query.split()[:8]),
            "cvssV3Severity": "CRITICAL",
            "pubStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "pubEndDate": end.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "resultsPerPage": max_results,
        }
        r = httpx.get(_NVD_CVES_URL, params=params, timeout=20)
        if r.status_code >= 400:
            params.pop("keywordSearch", None)
            r = httpx.get(_NVD_CVES_URL, params=params, timeout=20)
        data = r.json()
        out = []
        for item in data.get("vulnerabilities", [])[:max_results]:
            cve = item.get("cve", {})
            cve_id = cve.get("id", "CVE")
            descriptions = cve.get("descriptions") or []
            desc = next((d.get("value", "") for d in descriptions if d.get("lang") == "en"), "")
            metrics = cve.get("metrics", {})
            cvss = None
            for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                if metrics.get(key):
                    cvss = metrics[key][0]
                    break
            severity = ""
            score = ""
            if cvss:
                severity = cvss.get("cvssData", {}).get("baseSeverity") or cvss.get("baseSeverity", "")
                score = cvss.get("cvssData", {}).get("baseScore", "")
            refs = [ref.get("url", "") for ref in cve.get("references", {}).get("referenceData", [])[:5]]
            content = (
                f"CVE: {cve_id}\nSeverity: {severity} {score}\n"
                f"Published: {cve.get('published', '')}\nLast modified: {cve.get('lastModified', '')}\n"
                f"Description: {desc}\nReferences:\n" + "\n".join(refs)
            )
            out.append({
                "title": f"{cve_id} {severity}".strip(),
                "snippet": desc[:500],
                "content": content,
                "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                "source": "nvd",
            })
        return out
    except Exception:
        return []


def _cisa_kev_items(max_results: int = 5) -> list[dict]:
    """Fetch CISA Known Exploited Vulnerabilities as threat-intel documents."""
    try:
        import httpx
        r = httpx.get(_CISA_KEV_URL, timeout=20)
        data = r.json()
        vulns = data.get("vulnerabilities", [])
        vulns.sort(key=lambda v: v.get("dateAdded", ""), reverse=True)
        out = []
        for item in vulns[:max_results]:
            cve_id = item.get("cveID", "CVE")
            content = (
                f"CVE: {cve_id}\nVendor: {item.get('vendorProject', '')}\n"
                f"Product: {item.get('product', '')}\nDate added: {item.get('dateAdded', '')}\n"
                f"Due date: {item.get('dueDate', '')}\nKnown ransomware use: {item.get('knownRansomwareCampaignUse', '')}\n"
                f"Vulnerability: {item.get('vulnerabilityName', '')}\n"
                f"Action: {item.get('requiredAction', '')}\n"
                f"Notes: {item.get('notes', '')}"
            )
            out.append({
                "title": f"{cve_id} KEV {item.get('vendorProject', '')} {item.get('product', '')}".strip(),
                "snippet": item.get("vulnerabilityName", ""),
                "content": content,
                "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
                "source": "cisa-kev",
            })
        return out
    except Exception:
        return []


def _exploitdb_recent(query: str, max_results: int = 5) -> list[dict]:
    """Read the official Exploit-DB CSV and select rows matching the topic."""
    try:
        import httpx
        r = httpx.get(_EXPLOITDB_CSV_URL, timeout=20)
        keywords = {w.lower() for w in re.findall(r"[a-zA-Z0-9_-]{4,}", query)}
        rows = []
        reader = csv.DictReader(io.StringIO(r.text))
        for row in reader:
            title = row.get("description", "")
            haystack = " ".join([
                title,
                row.get("type", ""),
                row.get("platform", ""),
                row.get("codes", ""),
            ]).lower()
            score = sum(1 for kw in keywords if kw in haystack)
            if score <= 0:
                continue
            rows.append((score, row))
        rows.sort(key=lambda item: (item[0], item[1].get("date", "")), reverse=True)
        out = []
        for _, row in rows[:max_results]:
            exploit_id = row.get("id", "")
            title = row.get("description", "Exploit-DB entry")
            url = f"https://www.exploit-db.com/exploits/{exploit_id}" if exploit_id else "https://www.exploit-db.com/"
            content = (
                f"Exploit-DB ID: {exploit_id}\nTitle: {title}\nDate: {row.get('date', '')}\n"
                f"Author: {row.get('author', '')}\nType: {row.get('type', '')}\n"
                f"Platform: {row.get('platform', '')}\nPort: {row.get('port', '')}\n"
                f"Verified: {row.get('verified', '')}\nPath: {row.get('file', '')}\nCodes: {row.get('codes', '')}"
            )
            out.append({
                "title": f"Exploit-DB {exploit_id}: {title}",
                "snippet": content,
                "content": content,
                "url": url,
                "source": "exploit-db",
            })
        return out
    except Exception:
        return []


def _specialized_results(query: str, tags: list[str]) -> list[dict]:
    results = []
    tagset = set(tags)
    if "nvd" in tagset or "cve" in tagset:
        results.extend(_nvd_recent_cves(query))
    if "kev" in tagset or "threat-intel" in tagset:
        results.extend(_cisa_kev_items())
    if "exploit-db" in tagset or "exploit" in tagset:
        results.extend(_exploitdb_recent(query))
    return results


def _learn_topic(idx: int):
    """Ejecuta un ciclo de aprendizaje para el topic dado."""
    query, tags, platform, _ = INTEREST_MATRIX[idx]
    print(f"[Learner] Buscando: {query[:60]}...")

    results = _specialized_results(query, tags)
    results.extend(_web_search_raw(query, max_results=4))
    results = _rank_results(results, tags, limit=6)
    if not results:
        print(f"[Learner] Sin resultados para: {query[:40]}")
        return

    learned = []
    for res in results[:3]:  # máximo 3 páginas por ciclo
        url  = res.get("url", "")
        if not url or any(x in url for x in ["youtube.com", "reddit.com/r/", "twitter.com", "x.com"]):
            # Prioriza artículos técnicos, no vídeos ni redes sociales
            snippet_only = True
        else:
            snippet_only = False

        if res.get("content"):
            content = res["content"]
        elif snippet_only or not url.startswith("http"):
            # Solo guardar el snippet si no podemos fetch
            content = res.get("snippet", "")
        else:
            fetched = _fetch_url(url)
            content = fetched if len(fetched) > 200 else res.get("snippet", "")

        if len(content) < 100:
            continue

        title  = res.get("title", query[:60])
        doc_id = "learned_" + hashlib.md5((title + url).encode()).hexdigest()[:12]

        try:
            from app.rag.vectorstore import add_document
            add_document(
                doc_id=doc_id,
                title=f"[Auto] {title}",
                content=f"Fuente: {url}\n\n{content}",
                platform=platform,
                tags=tags + ["auto_learned", res.get("source", "web")],
            )
            learned.append(title[:80])
        except Exception as e:
            print(f"[Learner] RAG error: {e}")

    if learned:
        _log_entry(query, learned)
        print(f"[Learner] Guardados {len(learned)} docs - {', '.join(learned[:2])}")


def _log_entry(query: str, titles: list):
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts":    datetime.now().isoformat(),
            "query": query,
            "saved": titles,
        }
        with _LOG_LOCK:
            with open(_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Learner] Error escribiendo log: {e}")


def _learner_loop(interval_check: int = 1800):
    """Loop principal: cada interval_check segundos verifica si hay algo que aprender."""
    state = _load_state()
    # Aprende un topic al inicio (el más desactualizado)
    idx, should_run = _next_topic(state)
    if should_run and idx is not None:
        try:
            _learn_topic(idx)
            state[str(idx)] = time.time()
            _save_state(state)
        except Exception as e:
            print(f"[Learner] Error en ciclo inicial: {e}")

    while not _STOP_EVENT.is_set():
        _STOP_EVENT.wait(interval_check)
        if _STOP_EVENT.is_set():
            break

        state = _load_state()
        idx, should_run = _next_topic(state)
        if should_run and idx is not None:
            try:
                _learn_topic(idx)
                state[str(idx)] = time.time()
                _save_state(state)
            except Exception as e:
                print(f"[Learner] Error: {e}")


_learner_thread: threading.Thread | None = None

def start_learner(interval_check: int = 1800):
    """Inicia el learner en un hilo daemon. Protegido contra doble-arranque con lock."""
    global _learner_thread
    with _LEARNER_LOCK:
        if _learner_thread and _learner_thread.is_alive():
            return _learner_thread
        _STOP_EVENT.clear()
        _learner_thread = threading.Thread(
            target=_learner_loop, args=(interval_check,), daemon=True, name="AutonomousLearner"
        )
        _learner_thread.start()
    print(f"[Learner] Iniciado - verificando cada {interval_check//60} min")
    return _learner_thread


def stop_learner():
    _STOP_EVENT.set()


def get_log(last_n: int = 20) -> list[dict]:
    """Devuelve las últimas N entradas del log de aprendizaje."""
    if not _LOG_PATH.exists():
        return []
    lines = _LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
    entries = []
    for line in lines[-last_n:]:
        try:
            entries.append(json.loads(line))
        except Exception:
            pass
    return entries
