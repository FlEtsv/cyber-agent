# CyberAgent tools

CyberAgent exposes tools through `app/tools.py` and routes them with `app/tool_router.py`.
Each tool now has catalog metadata:

- `category`: core, web, files, system, desktop, network, forensics, encode, rag, self, mobile, or other.
- `risk`: `low` or `high`.
- `default_permission`: `auto` for low risk and `ask` for high risk.
- `guide`: short UI text explaining when the tool is appropriate.

## Permission model

High-risk tools require explicit approval unless the session is trusted or the user has allowed that tool:

- command/code execution: `shell`, `run_python`
- file/system mutation: `write_file`, package install/uninstall, process kill, environment changes
- active security checks: port scan, directory brute force, ping sweep, banner grab, crawl, DNS/whois/traceroute
- sensitive desktop access: keyboard/mouse actions, clipboard, credential lookup, self restart
- mobile tools marked dangerous by `app/mobile_tools.py`

The web and relay UI show the tool category and risk in action rows and approval cards. Browser session reports include the same metadata with arguments and result previews redacted.

## Authorized security workflow

For hacking/security tasks, work from low-impact reconnaissance to active checks:

1. `web_search`, `dns_lookup`, `whois_lookup` for passive context.
2. `ssl_info`, `http_headers_check`, `web_crawl` for web posture.
3. `port_scan`, `banner_grab`, `dir_bruteforce`, `ping_sweep` only on assets the user owns or has authorized.
4. `strings_extract`, `file_entropy`, `pe_info`, `registry_query`, `list_services`, `check_persistence` for local forensic analysis.
5. Summarize evidence, commands used, tool results, errors and next steps in the chat report.

## Router behavior

The router keeps core tools available and selects categories by LLM routing with keyword fallback. Requests mentioning hacking, pentest, recon, CVE, CTF, red team, blue team, OSINT or exposed services route to the `hacking` group, which combines network, web audit and local forensic tools.
