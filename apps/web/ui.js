/* ═══════════════════════════════════════════════════════════════════════════
   CyberAgent 2.0 — capa de UI: navegación por vistas, brain badge,
   catálogo de herramientas, galería de archivos y voz (TTS).
   Se engancha a la instancia `app` (app.js) sin modificar su lógica.
   ═══════════════════════════════════════════════════════════════════════════ */
(function () {
  'use strict';
  const app = window.app;
  const $ = (id) => document.getElementById(id);
  const FILES_KEY = 'ca_files_' + location.host;

  const state = {
    tools: [],
    files: [],
    view: 'view-chat',
    ttsOn: localStorage.getItem('ca_tts') === '1',
  };

  // ── Persistencia de archivos vistos (sobrevive recargas) ──────────────────
  try { state.files = JSON.parse(localStorage.getItem(FILES_KEY) || '[]'); } catch { state.files = []; }
  function saveFiles() {
    try { localStorage.setItem(FILES_KEY, JSON.stringify(state.files.slice(0, 120))); } catch {}
  }
  function mergeFiles(list) {
    if (!Array.isArray(list)) return;
    const byKey = new Map(state.files.map(f => [f.url || f.name, f]));
    list.forEach(f => { if (f && (f.url || f.name)) byKey.set(f.url || f.name, { ...byKey.get(f.url || f.name), mtime: Date.now() / 1000, ...f }); });
    state.files = Array.from(byKey.values()).sort((a, b) => (b.mtime || 0) - (a.mtime || 0));
    saveFiles();
  }

  // Badge numérico en un botón de la navegación (p.ej. archivos nuevos).
  function setNavBadge(viewId, count) {
    const btn = document.querySelector(`.nav-item[data-view="${viewId}"]`);
    if (!btn) return;
    let b = btn.querySelector('.nav-badge');
    if (count > 0) {
      if (!b) { b = document.createElement('span'); b.className = 'nav-badge'; (btn.querySelector('.nav-ico') || btn).appendChild(b); }
      b.textContent = count > 9 ? '9+' : String(count);
    } else if (b) { b.remove(); }
  }

  // Hook que llama app.js al recibir el evento entrante type:"files" (WEBPROD-029):
  // archivos generados por el agente → refresco en vivo o badge si no estás mirando.
  let _newFiles = 0;
  app.onServerFiles = function (list) {
    if (!Array.isArray(list) || !list.length) return;
    mergeFiles(list);
    if (state.view === 'view-files') { _newFiles = 0; renderFiles(); }
    else { _newFiles += list.length; setNavBadge('view-files', _newFiles); }
  };

  // ── Navegación entre vistas ───────────────────────────────────────────────
  function showView(viewId) {
    state.view = viewId;
    document.querySelectorAll('.view').forEach(v => v.classList.toggle('active', v.id === viewId));
    document.querySelectorAll('.nav-item[data-view]').forEach(n =>
      n.classList.toggle('active', n.dataset.view === viewId));
    if (viewId === 'view-tools') renderTools();
    if (viewId === 'view-files') { _newFiles = 0; setNavBadge('view-files', 0); loadDbFiles(); }
  }
  document.querySelectorAll('.nav-item[data-view]').forEach(btn =>
    btn.addEventListener('click', () => showView(btn.dataset.view)));
  const navSettings = $('nav-settings');
  if (navSettings) navSettings.addEventListener('click', () => {
    const sb = $('settings-btn'); if (sb) sb.click();
  });
  const brainBadge = $('brain-badge');
  if (brainBadge) brainBadge.addEventListener('click', () => { const sb = $('settings-btn'); if (sb) sb.click(); });

  // ── Brain badge (cerebro activo) ──────────────────────────────────────────
  function brainInfo() {
    const sel = (app && app.selectedModel) || '';
    const active = (app && app.activeModel) || '';
    const m = (sel || active || '').toLowerCase();
    if (!sel) {
      // Auto: depende de lo que el PC reporte como activo
      if (/mistral|magistral|pixtral/.test(m)) return { cls: '', icon: '🧠', name: 'Auto·Mistral' };
      return { cls: 'local', icon: '🔀', name: 'Auto' };
    }
    if (m === 'fused') return { cls: 'fused', icon: '🤝', name: 'Fusionado' };
    if (/codestral/.test(m)) return { cls: '', icon: '💻', name: 'Codestral' };
    if (/mistral-large/.test(m)) return { cls: '', icon: '🧠', name: 'Mistral L' };
    if (/mistral-medium/.test(m)) return { cls: '', icon: '🧠', name: 'Mistral M' };
    if (/mistral|magistral|pixtral/.test(m)) return { cls: '', icon: '🧠', name: 'Mistral' };
    // Local: muestra el nombre real del modelo para que SIEMPRE quede claro cuál corre
    const localName = (sel || active || 'local').replace(/:latest$/, '');
    return { cls: 'local', icon: '🖥️', name: localName };
  }
  function updateBrainBadge() {
    if (!brainBadge) return;
    const info = brainInfo();
    brainBadge.className = 'brain-badge ' + info.cls;
    const ic = brainBadge.querySelector('.brain-icon');
    const nm = brainBadge.querySelector('.brain-name');
    if (ic) ic.textContent = info.icon;
    if (nm) nm.textContent = info.name;
    const hint = $('brain-hint');
    if (hint) {
      hint.textContent = info.cls === 'fused'
        ? 'Mistral dirige y delega en el modelo local para tareas privadas/ofensivas.'
        : info.cls === 'local'
          ? 'Modelo local (sin nube). Privado y sin guardrails para trabajo autorizado.'
          : 'Mistral (nube) razona y trae búsqueda web, código e imágenes. Las tareas ofensivas se quedan en local.';
    }
  }
  const modelSelect = $('model-select');
  if (modelSelect) modelSelect.addEventListener('change', () => setTimeout(updateBrainBadge, 0));

  // ── Catálogo de herramientas ──────────────────────────────────────────────
  const CAT_ICON = {
    core: '⚙️', web: '🌐', files: '📄', system: '🖥️', network: '📡', hacking: '🛡️',
    forensics: '🔬', encode: '🔐', desktop: '🪟', media: '📷', rag: '📚', council: '🤝',
    studio: '🧠', documents: '📁', self: '♻️', otros: '🔧',
  };
  function permFor(name) {
    const p = (app && app.permissions) || {};
    return p[name] || 'ask';
  }
  function cyclePerm(name) {
    const order = ['ask', 'auto', 'block'];
    const cur = permFor(name);
    const next = order[(order.indexOf(cur) + 1) % order.length];
    if (app) { app.permissions = app.permissions || {}; app.permissions[name] = next; }
    try { app && app._savePreferences && app._savePreferences(); } catch {}
    return next;
  }
  function renderTools() {
    const grid = $('tools-grid');
    const countEl = $('tools-count');
    if (!grid) return;
    const q = ($('tools-search')?.value || '').toLowerCase().trim();
    let tools = state.tools;
    if (q) tools = tools.filter(t =>
      t.name.toLowerCase().includes(q) || (t.category || '').toLowerCase().includes(q) ||
      (t.description || '').toLowerCase().includes(q));
    if (countEl) countEl.textContent = `${tools.length} / ${state.tools.length}`;
    if (!state.tools.length) { grid.innerHTML = '<div class="tools-empty">Esperando catálogo del PC…</div>'; return; }
    grid.innerHTML = tools.map(t => {
      const perm = permFor(t.name);
      const risk = t.dangerous
        ? '<span class="tool-risk danger">RIESGO</span>'
        : '<span class="tool-risk safe">OK</span>';
      const params = (t.params || []).slice(0, 5).join(', ');
      return `<div class="tool-card">
        <div class="tool-card-top">
          <span class="tool-cat">${CAT_ICON[t.category] || '🔧'} ${t.category || ''}</span>
          ${risk}
        </div>
        <div class="tool-card-name">${t.name}</div>
        <div class="tool-card-desc">${(t.description || '').replace(/</g, '&lt;')}</div>
        ${params ? `<div class="tool-params">(${params})</div>` : ''}
        <div class="tool-card-foot">
          <button class="tool-perm" data-tool="${t.name}">permiso: ${perm}</button>
        </div>
      </div>`;
    }).join('');
    grid.querySelectorAll('.tool-perm').forEach(btn => btn.addEventListener('click', () => {
      const next = cyclePerm(btn.dataset.tool);
      btn.textContent = 'permiso: ' + next;
      try { app && app._renderPermissionsList && app._renderPermissionsList(); } catch {}
    }));
  }
  const toolsSearch = $('tools-search');
  if (toolsSearch) toolsSearch.addEventListener('input', renderTools);

  // ── Galería de archivos / resultados ──────────────────────────────────────
  const KIND_ICON = { image: '🖼️', pdf: '📕', doc: '📄', file: '📎' };
  function fmtBytes(n) {
    if (!n) return '';
    if (n < 1024) return n + ' B';
    if (n < 1048576) return (n / 1024).toFixed(0) + ' KB';
    return (n / 1048576).toFixed(1) + ' MB';
  }
  // WEBPROD-011/012: archivos de la BD (adjuntos por conversación + favoritos),
  // fusionados con los vistos en vivo (resultados de herramienta en localStorage).
  state.filter = 'all';
  state.dbFiles = [];

  async function loadDbFiles() {
    if (!app || typeof app._workspace !== 'function') { renderFiles(); return; }
    const payload = {};
    if (state.filter === 'conv') payload.conversation_id = app.currentConversationId || '__none__';
    if (state.filter === 'fav') payload.favorites_only = true;
    try {
      const r = await app._workspace('files_get', payload);
      state.dbFiles = Array.isArray(r.files) ? r.files : [];
    } catch { state.dbFiles = []; }
    // Apps/herramientas desplegadas por el agente en Cloudflare (sitio ordenado).
    try {
      const d = await app._workspace('deployments', {});
      state.deployments = Array.isArray(d.deployments) ? d.deployments : [];
    } catch { state.deployments = []; }
    renderFiles();
  }

  function _fileCard(f) {
    const url = f.url || '#';
    const name = (f.name || '').replace(/</g, '&lt;');
    const ext = (f.ext || (name.split('.').pop() || '')).toUpperCase();
    const isImg = f.kind === 'image' || /\.(png|jpe?g|webp|gif)$/i.test(name);
    const thumb = isImg && f.url ? `<img src="${url}" alt="${name}" loading="lazy">` : (KIND_ICON[f.kind] || '📎');
    const fav = f.id != null
      ? `<button class="file-fav ${f.favorite ? 'on' : ''}" data-fav="${f.id}" data-on="${f.favorite ? 1 : 0}" title="Favorito (persiste al borrar el chat)">${f.favorite ? '⭐' : '☆'}</button>`
      : '';
    return `<div class="file-card">${fav}
      <a class="file-open" href="${url}" target="_blank" rel="noopener">
        <div class="file-thumb">${thumb}</div>
        <div class="file-meta">
          <span class="file-name">${name}</span>
          <span class="file-info">${ext} ${fmtBytes(f.bytes)}</span>
        </div>
      </a></div>`;
  }

  function _deploymentsHtml() {
    const deps = (state.filter === 'all') ? (state.deployments || []) : [];
    if (!deps.length) return '';
    const rows = deps.map(d => {
      const url = d.url || '#';
      const kind = d.kind === 'static' ? '🌐' : '⚙️';
      return `<a class="dep-item" href="${url}" target="_blank" rel="noopener">
        <span class="dep-ic">${kind}</span>
        <span class="dep-meta"><b>${(d.name || d.slug || '').replace(/</g,'&lt;')}</b>
        <span class="dep-url">${String(url).replace(/^https?:\/\//,'').slice(0,46)}</span></span></a>`;
    }).join('');
    return `<div class="dep-section"><div class="cost-sec-title">🚀 Apps desplegadas (Cloudflare)</div>${rows}</div>`;
  }

  function renderFiles() {
    const grid = $('files-grid');
    if (!grid) return;
    const depHtml = _deploymentsHtml();
    let list;
    if (state.filter === 'all') {
      const seen = new Set(state.dbFiles.map(f => f.url || f.name));
      list = state.dbFiles.concat(state.files.filter(f => !seen.has(f.url || f.name)));
    } else {
      list = state.dbFiles;
    }
    if (!list.length && !depHtml) {
      const msg = state.filter === 'fav'
        ? 'No tienes favoritos. Marca ⭐ en cualquier archivo para conservarlo aunque borres la conversación.'
        : state.filter === 'conv'
          ? 'Esta conversación no tiene archivos adjuntos todavía.'
          : 'Aún no hay archivos. Adjunta un documento o pide al agente generar un PDF/imagen.';
      grid.innerHTML = depHtml + `<div class="files-empty">${msg}</div>`;
      return;
    }
    grid.innerHTML = depHtml + list.map(_fileCard).join('');
  }

  // Filtros Todos / Esta conversación / Favoritos
  document.querySelectorAll('#files-filter .files-tab').forEach(tab =>
    tab.addEventListener('click', () => {
      document.querySelectorAll('#files-filter .files-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      state.filter = tab.dataset.filter;
      loadDbFiles();
    }));

  // Toggle de favorito (delegado)
  const filesGrid = $('files-grid');
  if (filesGrid) filesGrid.addEventListener('click', async (e) => {
    const btn = e.target.closest('.file-fav');
    if (!btn) return;
    e.preventDefault();
    const id = Number(btn.dataset.fav);
    const on = btn.dataset.on === '1';
    if (app && typeof app._workspace === 'function') {
      await app._workspace('file_favorite', { file_id: id, favorite: !on });
      loadDbFiles();
    }
  });

  const filesRefresh = $('files-refresh');
  if (filesRefresh) filesRefresh.addEventListener('click', loadDbFiles);

  // Captura archivos de los resultados de herramienta en vivo
  function captureFromResult(result) {
    if (!result || typeof result !== 'object') return;
    const add = [];
    const pushUrl = (url, name) => {
      if (!url || typeof url !== 'string' || !/^https?:|^\/served\//.test(url)) return;
      const nm = name || url.split('/').pop();
      const ext = (nm.split('.').pop() || '').toLowerCase();
      const kind = ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext) ? 'image'
        : ext === 'pdf' ? 'pdf' : ['html', 'md', 'txt', 'docx'].includes(ext) ? 'doc' : 'file';
      add.push({ name: nm, url, ext, kind, bytes: result.bytes || 0, mtime: Date.now() / 1000 });
    };
    if (result.url) pushUrl(result.url, result.filename || result.name);
    if (Array.isArray(result.files)) result.files.forEach(x => x && pushUrl(x.url, (x.path || '').split(/[\\/]/).pop()));
    if (add.length) { mergeFiles(add); markNav('view-files'); if (state.view === 'view-files') renderFiles(); }
  }
  function markNav(viewId) {
    const nav = document.querySelector(`.nav-item[data-view="${viewId}"]`);
    if (nav && state.view !== viewId && !nav.querySelector('.nav-badge')) {
      const b = document.createElement('span'); b.className = 'nav-badge'; b.textContent = '•';
      nav.querySelector('.nav-lbl')?.appendChild(b);
    }
  }
  document.querySelectorAll('.nav-item[data-view]').forEach(btn =>
    btn.addEventListener('click', () => btn.querySelector('.nav-badge')?.remove()));

  // ── Voz: TTS de la respuesta final ────────────────────────────────────────
  function setTTS(on) {
    state.ttsOn = on; localStorage.setItem('ca_tts', on ? '1' : '0');
    const vb = $('voice-out-btn'); if (vb) { vb.classList.toggle('active', on); vb.title = on ? 'Voz activada (tocar para silenciar)' : 'Leer respuestas en voz alta'; }
    const vt = $('voice-out-toggle'); if (vt) vt.checked = on;
    if (!on && window.speechSynthesis) window.speechSynthesis.cancel();
  }
  function speak(text) {
    if (!state.ttsOn || !window.speechSynthesis || !text) return;
    const clean = text.replace(/```[\s\S]*?```/g, ' bloque de código ').replace(/[#*_`>]/g, '').slice(0, 600);
    if (!clean.trim()) return;
    try {
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(clean);
      u.lang = 'es-ES'; u.rate = 1.05;
      window.speechSynthesis.speak(u);
    } catch {}
  }
  const voiceOutBtn = $('voice-out-btn');
  if (voiceOutBtn) voiceOutBtn.addEventListener('click', () => setTTS(!state.ttsOn));
  const voiceOutToggle = $('voice-out-toggle');
  if (voiceOutToggle) voiceOutToggle.addEventListener('change', e => setTTS(e.target.checked));

  // ── Enganche al flujo de mensajes de app.js ───────────────────────────────
  if (app && typeof app._onMessage === 'function') {
    const orig = app._onMessage.bind(app);
    app._onMessage = function (evt) {
      try {
        const { type, data } = evt || {};
        if (type === 'connected') {
          if (data && data.tools) { state.tools = data.tools; }
          if (data && data.files) { mergeFiles(data.files); }
        } else if (type === 'tools') {
          state.tools = Array.isArray(data) ? data : (data?.tools || []);
          if (state.view === 'view-tools') renderTools();
        } else if (type === 'files') {
          mergeFiles(Array.isArray(data) ? data : (data?.files || []));
          if (state.view === 'view-files') renderFiles();
        } else if (type === 'tool_result') {
          captureFromResult(data?.result ?? data);
        } else if (type === 'done') {
          if (state.ttsOn && app.currentBubble) speak(app.currentBubble._raw);
        }
      } catch {}
      const r = orig(evt);
      try { updateBrainBadge(); } catch {}
      return r;
    };
  }

  // ── Bottom-sheet de conversaciones (móvil, manejable con una mano) ────────
  (function () {
    const panel = $('conversation-panel');
    const backdrop = $('chats-backdrop');
    const btn = $('chats-btn');
    if (!panel || !backdrop) return;
    const open = () => { panel.classList.add('sheet-open'); backdrop.classList.add('open'); };
    const close = () => { panel.classList.remove('sheet-open'); backdrop.classList.remove('open'); };
    if (btn) btn.addEventListener('click', () =>
      panel.classList.contains('sheet-open') ? close() : open());
    backdrop.addEventListener('click', close);
    // Cerrar el sheet al elegir o crear un chat (la acción la maneja app.js).
    const list = $('conversation-list');
    if (list) list.addEventListener('click', (e) => {
      if (e.target.closest('.conversation-item')) setTimeout(close, 140);
    });
    const nb = $('new-chat-btn');
    if (nb) nb.addEventListener('click', () => setTimeout(close, 140));
    // Cerrar con Escape
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') close(); });
  })();

  // ── Init ──────────────────────────────────────────────────────────────────
  setTTS(state.ttsOn);
  updateBrainBadge();
  setInterval(updateBrainBadge, 2000);
})();
