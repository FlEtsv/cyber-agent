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

  // ── Vista Seguridad: sub-pestañas ────────────────────────────────────────
  document.querySelectorAll('.sec-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.sec-tab').forEach(t => t.classList.remove('sec-tab-active'));
      document.querySelectorAll('.sec-panel').forEach(p => {
        p.classList.remove('sec-panel-active');
        p.style.display = 'none';
      });
      tab.classList.add('sec-tab-active');
      const panel = $('sec-panel-' + tab.dataset.sec);
      if (panel) { panel.style.display = 'flex'; panel.classList.add('sec-panel-active'); }
      if (tab.dataset.sec === 'learning') _loadLearningStats();
      if (tab.dataset.sec === 'cameras') _loadCameras();
    });
  });

  // ── Telegram: botón "Probar" ──────────────────────────────────────────────
  const secTgTest = $('sec-telegram-test');
  const secTgResult = $('sec-telegram-result');
  if (secTgTest) {
    secTgTest.addEventListener('click', async () => {
      secTgTest.disabled = true;
      secTgTest.textContent = '…';
      if (secTgResult) secTgResult.textContent = '';
      try {
        const r = await fetch('/api/notify/test', { method: 'POST' });
        const d = await r.json();
        secTgTest.textContent = d.ok ? '✅ enviado' : '❌ error';
        if (secTgResult) secTgResult.textContent = d.ok ? 'Mensaje enviado correctamente.' : (d.error || 'Error desconocido');
      } catch (e) {
        secTgTest.textContent = '❌ fallo';
        if (secTgResult) secTgResult.textContent = String(e);
      }
      setTimeout(() => { secTgTest.disabled = false; secTgTest.textContent = 'Probar notificación'; }, 3000);
    });
  }

  // ── Aprendizaje: stats del training_store ────────────────────────────────
  async function _loadLearningStats() {
    try {
      const r = await fetch('/api/training/stats');
      if (!r.ok) return;
      const d = await r.json();
      const set = (id, v) => { const el = $(id); if (el) el.textContent = v; };
      set('sl-total', d.total ?? '—');
      const bk = d.by_kind || {};
      set('sl-interaction', bk.interaction?.count ?? 0);
      set('sl-approval',    bk.approval?.count ?? 0);
      set('sl-feedback',    bk.feedback?.count ?? 0);
    } catch (_) {}
  }
  const refreshBtn = $('sec-training-refresh');
  if (refreshBtn) refreshBtn.addEventListener('click', _loadLearningStats);

  // ── G-02+G-03: Vault UI ──────────────────────────────────────────────────
  async function _loadVault() {
    const list = $('vault-list');
    if (!list) return;
    try {
      const r = await fetch('/api/vault/list');
      if (!r.ok) return;
      const d = await r.json();
      list.innerHTML = '';
      (d.secrets || []).forEach(s => {
        const row = document.createElement('div');
        row.className = 'vault-row';
        row.innerHTML = `<span class="vault-key">${s.key}</span><span class="vault-val">${s.masked}</span>`
          + `<button class="mini-btn vault-btn-reveal" data-key="${s.key}">Revelar</button>`;
        list.appendChild(row);
      });
      list.querySelectorAll('.vault-btn-reveal').forEach(btn => {
        btn.addEventListener('click', () => {
          const rr = $('vault-reveal-row');
          const ki = $('vault-reveal-key');
          if (rr) rr.style.display = 'flex';
          if (ki) ki.value = btn.dataset.key;
          const ti = $('vault-reveal-totp'); if (ti) { ti.value = ''; ti.focus(); }
          const res = $('vault-reveal-result'); if (res) res.textContent = '';
        });
      });
    } catch (_) {}
  }

  const vaultRevealBtn = $('vault-reveal-btn');
  if (vaultRevealBtn) {
    vaultRevealBtn.addEventListener('click', async () => {
      const key = ($('vault-reveal-key') || {}).value || '';
      const totp = ($('vault-reveal-totp') || {}).value || '';
      const res = $('vault-reveal-result');
      vaultRevealBtn.disabled = true;
      try {
        const r = await fetch('/api/vault/reveal', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({key, totp})
        });
        const d = await r.json();
        if (res) res.textContent = d.ok ? d.value : ('Error: ' + d.error);
      } catch (e) { if (res) res.textContent = String(e); }
      vaultRevealBtn.disabled = false;
    });
  }

  const vaultSaveBtn = $('vault-save-btn');
  if (vaultSaveBtn) {
    vaultSaveBtn.addEventListener('click', async () => {
      const key = ($('vault-new-key') || {}).value.trim();
      const value = ($('vault-new-val') || {}).value;
      const res = $('vault-save-result');
      if (!key) { if (res) res.textContent = 'Introduce un nombre de clave.'; return; }
      vaultSaveBtn.disabled = true;
      try {
        const r = await fetch('/api/vault/set', {
          method: 'POST', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({key, value})
        });
        const d = await r.json();
        if (res) res.textContent = d.ok ? '✅ guardado' : ('Error: ' + d.error);
        if (d.ok) { _loadVault(); if ($('vault-new-key')) $('vault-new-key').value = ''; if ($('vault-new-val')) $('vault-new-val').value = ''; }
      } catch (e) { if (res) res.textContent = String(e); }
      vaultSaveBtn.disabled = false;
    });
  }

  // ── N-01..N-06: Camera dashboard ────────────────────────────────────────────
  const _STATUS_LABELS = { online: '🟢 online', offline: '🔴 offline', unknown: '⚪ desconocido' };

  function _camCard(cam) {
    const card = document.createElement('div');
    card.className = 'sec-cam-card';
    card.dataset.camId = cam.id;
    const status = cam.enabled ? 'unknown' : 'offline';
    card.innerHTML = `
      <div class="sec-cam-thumb sec-cam-thumb-real">
        <span class="sec-cam-no-stream">📷</span>
      </div>
      <div class="sec-cam-info">
        <div class="sec-cam-name">${escHtml(cam.name)}</div>
        <div class="sec-cam-meta">${escHtml(cam.kind)} · ${escHtml(cam.location || '—')}</div>
        <div class="sec-cam-status">${_STATUS_LABELS[status]}</div>
      </div>
      <div class="sec-cam-card-actions">
        <button class="mini-btn cam-ctx-btn" title="Abrir agente con contexto de esta cámara">🤖 Contexto</button>
        <button class="mini-btn cam-del-btn" title="Eliminar cámara">🗑️</button>
      </div>`;
    card.querySelector('.cam-ctx-btn').addEventListener('click', () => {
      // N-05: abrir chat con contexto de la cámara
      const msg = `Analiza la cámara "${cam.name}" (${cam.kind}, fuente: ${cam.source_url || '—'}, ubicación: ${cam.location || '—'}).`;
      if (window._cyberApp && window._cyberApp.sendMessage) {
        window._cyberApp.sendMessage(msg);
      } else {
        const input = document.getElementById('user-input');
        if (input) { input.value = msg; input.focus(); }
      }
      // N-04: volver a la vista principal del agente
      const navHome = document.querySelector('[data-view="view-chat"]');
      if (navHome) navHome.click();
    });
    card.querySelector('.cam-del-btn').addEventListener('click', async () => {
      if (!confirm(`¿Eliminar cámara "${cam.name}"?`)) return;
      await fetch(`/api/cameras/${cam.id}`, { method: 'DELETE' });
      _loadCameras();
    });
    return card;
  }

  async function _loadCameras() {
    const grid = $('cam-grid');
    if (!grid) return;
    grid.innerHTML = '<div class="sec-cam-placeholder cam-loading">Cargando…</div>';
    try {
      const r = await fetch('/api/cameras');
      if (!r.ok) { grid.innerHTML = '<div class="sec-cam-placeholder">Error cargando cámaras</div>'; return; }
      const d = await r.json();
      grid.innerHTML = '';
      if (!d.cameras || d.cameras.length === 0) {
        grid.innerHTML = '<div class="sec-cam-placeholder">Sin cámaras registradas — usa "+ Añadir cámara"</div>';
        return;
      }
      d.cameras.forEach(cam => grid.appendChild(_camCard(cam)));
    } catch (e) {
      grid.innerHTML = '<div class="sec-cam-placeholder">Error: ' + escHtml(String(e)) + '</div>';
    }
  }

  const camRefreshBtn = $('cam-refresh-btn');
  if (camRefreshBtn) camRefreshBtn.addEventListener('click', _loadCameras);

  // N-03: modal añadir cámara
  const camAddBtn = $('cam-add-btn');
  const camModal = $('cam-modal');
  const camModalCancel = $('cam-modal-cancel');
  const camModalSave = $('cam-modal-save');
  const camModalErr = $('cam-modal-err');

  if (camAddBtn) camAddBtn.addEventListener('click', () => {
    if (camModal) camModal.style.display = 'flex';
  });
  if (camModalCancel) camModalCancel.addEventListener('click', () => {
    if (camModal) camModal.style.display = 'none';
    if (camModalErr) camModalErr.style.display = 'none';
  });
  if (camModalSave) camModalSave.addEventListener('click', async () => {
    const name = ($('cam-f-name') || {}).value || '';
    const kind = ($('cam-f-kind') || {}).value || 'interior';
    const source_type = ($('cam-f-source-type') || {}).value || 'ha';
    const source_url = ($('cam-f-source-url') || {}).value || '';
    const location = ($('cam-f-location') || {}).value || '';
    if (!name.trim()) { if (camModalErr) { camModalErr.textContent = 'El nombre es obligatorio'; camModalErr.style.display = ''; } return; }
    try {
      const r = await fetch('/api/cameras', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, kind, source_type, source_url, location }),
      });
      const d = await r.json();
      if (!d.ok) { if (camModalErr) { camModalErr.textContent = d.error || 'Error'; camModalErr.style.display = ''; } return; }
      if (camModal) camModal.style.display = 'none';
      if (camModalErr) camModalErr.style.display = 'none';
      ['cam-f-name', 'cam-f-source-url', 'cam-f-location'].forEach(id => { const el = $(id); if (el) el.value = ''; });
      _loadCameras();
    } catch (e) { if (camModalErr) { camModalErr.textContent = String(e); camModalErr.style.display = ''; } }
  });

  // ── AE-01..AE-03: Training model list in settings ───────────────────────────
  async function _loadTrainingModels() {
    const list = $('training-model-list');
    if (!list) return;
    list.innerHTML = '<div class="training-loading">Cargando…</div>';
    try {
      const r = await fetch('/api/training/models');
      if (!r.ok) { list.innerHTML = '<div class="training-loading">Error cargando modelos</div>'; return; }
      const d = await r.json();
      if (!d.ok || !d.models) { list.innerHTML = '<div class="training-loading">Sin datos</div>'; return; }
      list.innerHTML = '';
      d.models.forEach(m => {
        const row = document.createElement('div');
        row.className = 'training-model-row' + (m.ready ? ' training-model-ready' : '');
        const pct = m.progress_pct || 0;
        const badge = m.ready ? '<span class="training-badge-ready">✅ Listo</span>' : '';
        row.innerHTML = `
          <div class="training-model-header">
            <span class="training-model-name">${escHtml(m.model_id)}</span>
            ${badge}
          </div>
          <div class="training-progress-bar-wrap">
            <div class="training-progress-bar" style="width:${pct}%"></div>
          </div>
          <div class="training-model-meta">${m.count || 0} / ${m.threshold || '?'} ejemplos · ${pct}%</div>`;
        if (m.ready) {
          const trainBtn = document.createElement('button');
          trainBtn.className = 'mini-btn training-train-btn';
          trainBtn.textContent = `Entrenar ${m.model_id}`;
          trainBtn.addEventListener('click', async () => {
            trainBtn.textContent = 'Calculando…';
            try {
              const er = await fetch(`/api/training/estimate/${encodeURIComponent(m.model_id)}`);
              const ed = await er.json();
              if (ed.ok) {
                const msg = `Estimación para ${m.model_id}:\n• VRAM: ${ed.vram_train_gb} GB\n• Tiempo: ~${ed.hours_estimate}h\n• GPU: ${ed.gpu_recommended}\n• Coste RunPod: $${ed.runpod_cost_usd}\n\n¿Iniciar entrenamiento?`;
                if (confirm(msg)) {
                  trainBtn.textContent = '⏳ Iniciando…';
                  // AE-04: llamar al endpoint de entrenamiento (AF section)
                  const tr = await fetch('/api/training/start', {
                    method: 'POST', headers: {'Content-Type':'application/json'},
                    body: JSON.stringify({model_id: m.model_id}),
                  });
                  const td = await tr.json();
                  trainBtn.textContent = td.ok ? '🚀 Iniciado' : ('Error: ' + td.error);
                }
              }
            } catch (e) {
              trainBtn.textContent = 'Error: ' + e.message;
            }
          });
          row.appendChild(trainBtn);
        }
        list.appendChild(row);
      });
    } catch (e) {
      list.innerHTML = '<div class="training-loading">Error: ' + escHtml(String(e)) + '</div>';
    }
  }

  const trainingRefreshBtn = $('training-refresh-btn');
  if (trainingRefreshBtn) trainingRefreshBtn.addEventListener('click', _loadTrainingModels);

  // Cargar vault cuando se abre el panel de ajustes
  const settingsBtn2 = $('settings-btn');
  if (settingsBtn2) settingsBtn2.addEventListener('click', () => {
    setTimeout(_loadVault, 200);
    setTimeout(_loadTrainingModels, 300);
  });

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

  // ── O-01..O-06: Vista individual de cámara con IA en vivo ─────────────────
  let _liveEventSource = null;
  let _currentCamDetail = null;

  function _openCamDetail(cam) {
    _currentCamDetail = cam;
    // Cambiar de panel cameras al panel cam-detail
    document.querySelectorAll('.sec-panel').forEach(p => p.classList.remove('sec-panel-active'));
    const dp = $('sec-panel-cam-detail');
    if (dp) { dp.classList.add('sec-panel-active'); dp.style.display = ''; }

    // Rellenar encabezado
    const nameEl = $('cam-detail-name');
    const metaEl = $('cam-detail-meta');
    if (nameEl) nameEl.textContent = cam.name || cam.id;
    if (metaEl) metaEl.textContent = (cam.kind || '') + ' · ' + (cam.location || cam.source_url || '—');

    // Iniciar stream en vivo
    _startLiveStream(cam);
    _loadCamDetections(cam.id || cam.name);
    _loadCamTimeline(cam.id || cam.name);
    _loadCamZones(cam.id || cam.name);
    _loadCatList();
  }

  function _closeCamDetail() {
    _stopLiveStream();
    _currentCamDetail = null;
    document.querySelectorAll('.sec-panel').forEach(p => p.classList.remove('sec-panel-active'));
    const cp = $('sec-panel-cameras');
    if (cp) cp.classList.add('sec-panel-active');
    const dp = $('sec-panel-cam-detail');
    if (dp) dp.style.display = 'none';
  }

  const camDetailBack = $('cam-detail-back');
  if (camDetailBack) camDetailBack.addEventListener('click', _closeCamDetail);

  function _startLiveStream(cam) {
    _stopLiveStream();
    const img = $('cam-live-img');
    const placeholder = $('cam-live-placeholder');
    const badge = $('cam-live-badge');
    const reasoningEl = $('cam-ai-reasoning');
    const threatEl = $('cam-ai-threat');

    const camId = cam.name || cam.id;
    const es = new EventSource(`/security/cameras/${encodeURIComponent(camId)}/live`);
    _liveEventSource = es;

    es.addEventListener('snapshot', e => {
      try {
        const data = JSON.parse(e.data);
        if (data.image_b64 && img) {
          img.src = 'data:image/jpeg;base64,' + data.image_b64;
          img.style.display = '';
          if (placeholder) placeholder.style.display = 'none';
          if (badge) badge.style.display = '';
        }
      } catch {}
    });

    es.addEventListener('reasoning', e => {
      try {
        const data = JSON.parse(e.data);
        if (reasoningEl) reasoningEl.textContent = data.text || '';
        if (threatEl) {
          const score = Math.round((data.threat_score || 0) * 100);
          const action = data.action || 'ignore';
          const color = score > 60 ? '#f85149' : score > 30 ? '#f0883e' : '#3fb950';
          threatEl.innerHTML = `<span style="color:${color}">Amenaza: ${score}% · ${action}</span>`;
        }
      } catch {}
    });

    es.addEventListener('detection', e => {
      try {
        const data = JSON.parse(e.data);
        _addDetection(data);
        // AJ-08: si detecta gato, preguntar "¿es Michi?"
        if (data.type === 'cat' || (data.description || '').toLowerCase().includes('gat')) {
          _showCatConfirm(data);
        }
      } catch {}
    });

    es.addEventListener('error', () => {
      if (placeholder) placeholder.innerHTML = '<span>🚫 Stream no disponible (SECURITY_ENABLED=0)</span>';
      if (badge) badge.style.display = 'none';
    });
  }

  function _stopLiveStream() {
    if (_liveEventSource) { _liveEventSource.close(); _liveEventSource = null; }
    const img = $('cam-live-img');
    const placeholder = $('cam-live-placeholder');
    const badge = $('cam-live-badge');
    if (img) { img.style.display = 'none'; img.src = ''; }
    if (placeholder) { placeholder.style.display = ''; placeholder.innerHTML = '<span>🎥 Stream detenido</span>'; }
    if (badge) badge.style.display = 'none';
  }

  function _addDetection(data) {
    const list = $('cam-detections-list');
    if (!list) return;
    const row = document.createElement('div');
    row.className = 'cam-detection-row';
    const score = Math.round((data.threat_score || data.confidence || 0) * 100);
    const ts = new Date().toLocaleTimeString();
    row.innerHTML = `<span class="cam-det-ts">${ts}</span><span class="cam-det-type">${escHtml(data.type || 'objeto')}</span><span class="cam-det-desc">${escHtml(data.description || '')}</span><span class="cam-det-score">${score}%</span>`;
    list.insertBefore(row, list.firstChild);
    // Mantener máximo 20 detecciones
    while (list.children.length > 20) list.removeChild(list.lastChild);
  }

  // AJ-08: Confirmar "¿es Michi?"
  function _showCatConfirm(detection) {
    const panel = $('cam-cat-confirm');
    const question = $('cam-cat-question');
    if (!panel) return;
    const catName = detection.pet_id || 'el gato detectado';
    if (question) question.textContent = `¿Es ${catName}?`;
    panel.style.display = '';
    // Auto-ocultar en 15 s
    setTimeout(() => { if (panel) panel.style.display = 'none'; }, 15000);
  }

  const camCatYes = $('cam-cat-yes');
  const camCatNo = $('cam-cat-no');
  if (camCatYes) camCatYes.addEventListener('click', async () => {
    if (!_currentCamDetail) return;
    const camId = _currentCamDetail.name || _currentCamDetail.id;
    await fetch('/api/security/cat-feedback', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({cam_id: camId, confirmed: true, signal: 1.0}),
    }).catch(() => {});
    const panel = $('cam-cat-confirm');
    if (panel) panel.style.display = 'none';
  });
  if (camCatNo) camCatNo.addEventListener('click', async () => {
    if (!_currentCamDetail) return;
    const camId = _currentCamDetail.name || _currentCamDetail.id;
    const correctCat = ($('cam-cat-select') || {}).value || '';
    await fetch('/api/security/cat-feedback', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({cam_id: camId, confirmed: false, correct_pet: correctCat, signal: -1.0}),
    }).catch(() => {});
    const panel = $('cam-cat-confirm');
    if (panel) panel.style.display = 'none';
  });

  async function _loadCatList() {
    try {
      const r = await fetch('/api/security/pets');
      if (!r.ok) return;
      const d = await r.json();
      const sel = $('cam-cat-select');
      if (!sel || !d.pets) return;
      sel.innerHTML = '<option value="">¿Cuál es?</option>';
      d.pets.forEach(p => {
        const o = document.createElement('option');
        o.value = p.id || p.name;
        o.textContent = p.name;
        sel.appendChild(o);
      });
    } catch {}
  }

  async function _loadCamDetections(camId) {
    const list = $('cam-detections-list');
    if (!list) return;
    try {
      const r = await fetch(`/api/security/events?cam_id=${encodeURIComponent(camId)}&n=10`);
      if (!r.ok) { list.innerHTML = '<div class="comms-loading">Sin datos</div>'; return; }
      const d = await r.json();
      list.innerHTML = '';
      (d.events || []).forEach(ev => {
        const row = document.createElement('div');
        row.className = 'cam-detection-row';
        const ts = ev.ts ? new Date(ev.ts * 1000).toLocaleTimeString() : '—';
        row.innerHTML = `<span class="cam-det-ts">${ts}</span><span class="cam-det-type">${escHtml(ev.event_type || '')}</span><span class="cam-det-desc">${escHtml(ev.description || '')}</span>`;
        list.appendChild(row);
      });
    } catch {}
  }

  async function _loadCamTimeline(camId) {
    const list = $('cam-timeline-list');
    if (!list) return;
    try {
      const r = await fetch(`/api/security/events?cam_id=${encodeURIComponent(camId)}&n=20`);
      if (!r.ok) { list.innerHTML = '<div class="comms-loading">Sin eventos</div>'; return; }
      const d = await r.json();
      list.innerHTML = '';
      (d.events || []).forEach(ev => {
        const item = document.createElement('div');
        item.className = 'sec-tl-item';
        const ts = ev.ts ? new Date(ev.ts * 1000).toLocaleTimeString() : '—';
        const color = ev.event_type === 'intrusion' ? 'sec-tl-red' : ev.event_type === 'motion' ? 'sec-tl-yellow' : 'sec-tl-green';
        item.innerHTML = `<span class="sec-tl-dot ${color}"></span><span class="sec-tl-ts">${ts}</span><span>${escHtml(ev.event_type || '')} — ${escHtml(ev.description || '')}</span>`;
        list.appendChild(item);
      });
    } catch {}
  }

  async function _loadCamZones(camId) {
    const list = $('cam-zones-list');
    if (!list) return;
    try {
      const r = await fetch(`/api/security/zones?cam_id=${encodeURIComponent(camId)}`);
      if (!r.ok) { list.innerHTML = '<div class="comms-loading">Sin zonas</div>'; return; }
      const d = await r.json();
      list.innerHTML = '';
      (d.zones || []).forEach(z => {
        const row = document.createElement('div');
        row.className = 'cam-zone-row';
        const typeLabel = z.zone_type === 'warning' ? '⚠️ Alerta' : '✅ Segura';
        row.innerHTML = `<span class="cam-zone-type">${typeLabel}</span><span class="cam-zone-name">${escHtml(z.name || 'Zona ' + z.id)}</span><button class="mini-btn cam-zone-del" data-id="${z.id}">🗑️</button>`;
        row.querySelector('.cam-zone-del').addEventListener('click', async () => {
          await fetch(`/api/security/zones/${z.id}`, {method:'DELETE'}).catch(() => {});
          _loadCamZones(camId);
        });
        list.appendChild(row);
      });
      if (!d.zones || d.zones.length === 0) list.innerHTML = '<div class="comms-loading">Sin zonas definidas</div>';
    } catch {}
  }

  const camZoneAdd = $('cam-zone-add');
  if (camZoneAdd) camZoneAdd.addEventListener('click', async () => {
    if (!_currentCamDetail) return;
    const name = prompt('Nombre de la zona:');
    if (!name) return;
    const type = confirm('¿Es zona de ALERTA (OK=Alerta, Cancel=Segura)?') ? 'warning' : 'safe';
    const camId = _currentCamDetail.name || _currentCamDetail.id;
    await fetch('/api/security/zones', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({cam_id: camId, name, zone_type: type, polygon: [[0.1,0.1],[0.9,0.1],[0.9,0.9],[0.1,0.9]]}),
    }).catch(() => {});
    _loadCamZones(camId);
  });

  // Conectar el click en tarjeta de cámara para abrir detalle
  const origCamCard = typeof _camCard !== 'undefined' ? _camCard : null;
  document.addEventListener('click', e => {
    const card = e.target.closest('.sec-cam-card');
    if (card && card._camData) _openCamDetail(card._camData);
  });

  // Grabar desde la vista de detalle
  const camDetailRecord = $('cam-detail-record');
  if (camDetailRecord) camDetailRecord.addEventListener('click', async () => {
    if (!_currentCamDetail) return;
    const camId = _currentCamDetail.name || _currentCamDetail.id;
    const duration = parseInt(prompt('Duración (segundos, máx 300):', '60') || '60', 10);
    try {
      const r = await fetch(`/security/cameras/${encodeURIComponent(camId)}/record`, {
        method: 'POST', headers: {'Content-Type':'application/json', 'X-Event-Token': 'local'},
        body: JSON.stringify({duration}),
      });
      const d = await r.json();
      camDetailRecord.textContent = d.ok ? '⏺ Grabando' : '✗ Error';
      setTimeout(() => { camDetailRecord.textContent = '⏺ Grabar'; }, 5000);
    } catch {}
  });

  // ── P-03..P-08: Panel de grabaciones ──────────────────────────────────────
  const secPanelRecordings = $('sec-panel-recordings');
  async function _loadRecordings(camId) {
    const list = $('recordings-list');
    if (!list) return;
    list.innerHTML = '<div class="comms-loading">Cargando…</div>';
    try {
      const url = camId
        ? `/security/cameras/${encodeURIComponent(camId)}/recordings`
        : '/api/security/recordings';
      const r = await fetch(url);
      if (!r.ok) { list.innerHTML = '<div class="comms-loading">Error o módulo desactivado</div>'; return; }
      const d = await r.json();
      const recs = d.recordings || [];
      if (recs.length === 0) { list.innerHTML = '<div class="comms-loading">Sin grabaciones</div>'; return; }
      list.innerHTML = '';
      recs.forEach(rec => {
        const row = document.createElement('div');
        row.className = 'recording-row';
        const ts = rec.started_at ? new Date(rec.started_at * 1000).toLocaleString() : '—';
        const size = rec.size_bytes ? Math.round(rec.size_bytes / 1024) + ' KB' : '—';
        const dur = rec.duration ? rec.duration + 's' : '—';
        row.innerHTML = `
          <div class="rec-thumb">${rec.thumb_b64 ? '<img src="data:image/jpeg;base64,' + rec.thumb_b64 + '" class="rec-thumb-img">' : '🎬'}</div>
          <div class="rec-info">
            <div class="rec-cam">${escHtml(rec.cam_id || '—')}</div>
            <div class="rec-ts">${ts} · ${dur} · ${size}</div>
            <div class="rec-trigger">${escHtml(rec.trigger || 'manual')}</div>
          </div>
          <div class="rec-actions">
            <button class="mini-btn rec-play-btn" data-path="${escHtml(rec.path || '')}">▶</button>
            <a class="mini-btn" href="/download/${encodeURIComponent(rec.path || '')}" download>⬇</a>
          </div>`;
        row.querySelector('.rec-play-btn').addEventListener('click', (e) => {
          const path = e.target.dataset.path;
          _playRecording(path, rec);
        });
        list.appendChild(row);
      });
    } catch (err) {
      list.innerHTML = '<div class="comms-loading">Error: ' + escHtml(String(err)) + '</div>';
    }
  }

  function _playRecording(path, rec) {
    const player = $('recording-player');
    const video = $('rec-video');
    const meta = $('rec-player-meta');
    if (!player || !video) return;
    player.style.display = '';
    video.src = '/served/' + encodeURIComponent(path);
    video.play().catch(() => {});
    if (meta) {
      const ts = rec.started_at ? new Date(rec.started_at * 1000).toLocaleString() : '—';
      meta.textContent = `${rec.cam_id || '—'} · ${ts} · ${rec.trigger || '—'}`;
    }
  }

  const recCloseBtn = $('rec-close-btn');
  if (recCloseBtn) recCloseBtn.addEventListener('click', () => {
    const player = $('recording-player');
    const video = $('rec-video');
    if (video) video.pause();
    if (player) player.style.display = 'none';
  });

  const recCamFilter = $('rec-cam-filter');
  if (recCamFilter) recCamFilter.addEventListener('change', () => {
    _loadRecordings(recCamFilter.value);
  });

  // ── AL-09: Heatmap de patrones ─────────────────────────────────────────────
  async function _renderHeatmap(catId) {
    const canvas = $('heatmap-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#0d1117';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    try {
      const url = catId
        ? `/api/security/heatmap?cat_id=${encodeURIComponent(catId)}`
        : '/api/security/heatmap';
      const r = await fetch(url);
      if (!r.ok) { _drawHeatmapNoData(ctx, canvas); return; }
      const d = await r.json();
      if (!d.points || d.points.length === 0) { _drawHeatmapNoData(ctx, canvas); return; }
      _drawHeatmapPoints(ctx, canvas, d.points);
      _loadHeatmapSchedules(d.schedules || []);
      _loadHeatmapRoutes(d.routes || []);
    } catch {
      _drawHeatmapNoData(ctx, canvas);
    }
  }

  function _drawHeatmapPoints(ctx, canvas, points) {
    const W = canvas.width, H = canvas.height;
    const maxCount = Math.max(...points.map(p => p.count || 1), 1);
    points.forEach(p => {
      const x = (p.x || 0) * W;
      const y = (p.y || 0) * H;
      const r = 30 * Math.sqrt((p.count || 1) / maxCount) + 5;
      const alpha = 0.15 + 0.6 * (p.count || 1) / maxCount;
      const grad = ctx.createRadialGradient(x, y, 0, x, y, r);
      grad.addColorStop(0, `rgba(88,166,255,${alpha})`);
      grad.addColorStop(1, 'rgba(88,166,255,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    });
  }

  function _drawHeatmapNoData(ctx, canvas) {
    ctx.fillStyle = '#8b949e';
    ctx.font = '16px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Sin datos — SECURITY_ENABLED=0 o sin tracking activo', canvas.width / 2, canvas.height / 2);
  }

  function _loadHeatmapSchedules(schedules) {
    const grid = $('heatmap-schedule-grid');
    if (!grid) return;
    grid.innerHTML = '';
    if (!schedules.length) { grid.innerHTML = '<div class="comms-loading">Sin datos de horario</div>'; return; }
    schedules.forEach(s => {
      const cell = document.createElement('div');
      cell.className = 'heatmap-schedule-cell';
      const intensity = Math.round((s.intensity || 0) * 100);
      cell.style.opacity = 0.3 + (s.intensity || 0) * 0.7;
      cell.innerHTML = `<span class="hms-hour">${s.hour}h</span><span class="hms-int">${intensity}%</span>`;
      grid.appendChild(cell);
    });
  }

  function _loadHeatmapRoutes(routes) {
    const list = $('heatmap-routes-list');
    if (!list) return;
    list.innerHTML = '';
    if (!routes.length) { list.innerHTML = '<div class="comms-loading">Sin rutas registradas</div>'; return; }
    routes.forEach(r => {
      const row = document.createElement('div');
      row.className = 'heatmap-route-row';
      row.innerHTML = `<span>${escHtml(r.from_zone || '—')} → ${escHtml(r.to_zone || '—')}</span><span class="heatmap-route-freq">${r.count || 0}x</span>`;
      list.appendChild(row);
    });
  }

  const heatmapRefresh = $('heatmap-refresh');
  if (heatmapRefresh) heatmapRefresh.addEventListener('click', () => {
    const catSel = $('heatmap-cat-select');
    _renderHeatmap(catSel ? catSel.value : '');
  });

  const heatmapCatSelect = $('heatmap-cat-select');
  if (heatmapCatSelect) heatmapCatSelect.addEventListener('change', () => {
    _renderHeatmap(heatmapCatSelect.value);
  });

  // ── AS-01..AS-05: Config de comms ─────────────────────────────────────────
  async function _loadCommsChannels() {
    const list = $('comms-channels-list');
    if (!list) return;
    try {
      const r = await fetch('/api/comms/config');
      if (!r.ok) { list.innerHTML = '<div class="comms-loading">Módulo desactivado o sin config</div>'; return; }
      const d = await r.json();
      const channels = d.channels || [];
      list.innerHTML = '';
      if (!channels.length) { list.innerHTML = '<div class="comms-loading">Sin canales configurados</div>'; return; }
      channels.forEach(ch => {
        const row = document.createElement('div');
        row.className = 'comms-channel-row';
        row.innerHTML = `<span class="comms-ch-name">${escHtml(ch.name || ch.id)}</span><span class="comms-ch-topic">${escHtml(ch.topic_id || 'principal')}</span><span class="comms-ch-severity">${escHtml(ch.severity || 'TODAS')}</span>`;
        list.appendChild(row);
      });
    } catch {
      list.innerHTML = '<div class="comms-loading">Error cargando canales</div>';
    }
  }

  async function _loadCommsTemplates() {
    const list = $('comms-templates-list');
    if (!list) return;
    try {
      const r = await fetch('/api/comms/templates');
      if (!r.ok) { list.innerHTML = '<div class="comms-loading">Sin plantillas</div>'; return; }
      const d = await r.json();
      list.innerHTML = '';
      (d.templates || []).forEach(t => {
        const row = document.createElement('div');
        row.className = 'comms-template-row';
        row.innerHTML = `<span class="comms-tpl-type">${escHtml(t.type || t.id)}</span><span class="comms-tpl-preview">${escHtml((t.template || '').substring(0, 80))}${(t.template || '').length > 80 ? '…' : ''}</span>`;
        list.appendChild(row);
      });
      if (!d.templates || !d.templates.length) list.innerHTML = '<div class="comms-loading">Sin plantillas personalizadas</div>';
    } catch {
      list.innerHTML = '<div class="comms-loading">Error cargando plantillas</div>';
    }
  }

  const commsNdSave = $('comms-nd-save');
  if (commsNdSave) commsNdSave.addEventListener('click', async () => {
    const from = ($('comms-nd-from') || {}).value || '22:00';
    const to = ($('comms-nd-to') || {}).value || '08:00';
    await fetch('/api/comms/no-disturb', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({from, to}),
    }).catch(() => {});
    commsNdSave.textContent = '✓ Guardado';
    setTimeout(() => { commsNdSave.textContent = 'Guardar'; }, 2000);
  });

  const commsDigestSave = $('comms-digest-save');
  if (commsDigestSave) commsDigestSave.addEventListener('click', async () => {
    const min = parseInt(($('comms-digest-min') || {}).value || '30', 10);
    await fetch('/api/comms/digest-config', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({interval_minutes: min}),
    }).catch(() => {});
    commsDigestSave.textContent = '✓ Guardado';
    setTimeout(() => { commsDigestSave.textContent = 'Guardar'; }, 2000);
  });

  const commsDigestFlush = $('comms-digest-flush');
  if (commsDigestFlush) commsDigestFlush.addEventListener('click', async () => {
    const r = await fetch('/api/comms/digest-flush', {method: 'POST'}).catch(() => null);
    const d = r ? await r.json().catch(() => ({})) : {};
    commsDigestFlush.textContent = d.ok ? '✓ Enviado' : '✗ Error';
    setTimeout(() => { commsDigestFlush.textContent = 'Enviar ahora'; }, 3000);
  });

  const commsTestSend = $('comms-test-send');
  const commsTestResult = $('comms-test-result');
  if (commsTestSend) commsTestSend.addEventListener('click', async () => {
    const topic = ($('comms-test-topic') || {}).value || 'notifications';
    try {
      const r = await fetch('/api/comms/test', {
        method: 'POST', headers: {'Content-Type':'application/json'},
        body: JSON.stringify({topic}),
      });
      const d = await r.json();
      if (commsTestResult) commsTestResult.textContent = d.ok ? '✓ Enviado' : '✗ ' + (d.error || 'Error');
    } catch (e) {
      if (commsTestResult) commsTestResult.textContent = '✗ ' + e.message;
    }
  });

  // Cargar datos al cambiar al sub-panel comms/heatmap/recordings
  const origSecTabHandler = document.querySelector('#sec-tabs');
  if (origSecTabHandler) {
    origSecTabHandler.addEventListener('click', e => {
      const btn = e.target.closest('.sec-tab');
      if (!btn) return;
      const sec = btn.dataset.sec;
      if (sec === 'heatmap') {
        const catSel = $('heatmap-cat-select');
        _renderHeatmap(catSel ? catSel.value : '');
        _loadCatListForHeatmap();
      } else if (sec === 'recordings') {
        const camSel = $('rec-cam-filter');
        _loadRecordings(camSel ? camSel.value : '');
        _loadCamsForRecFilter();
      } else if (sec === 'comms') {
        _loadCommsChannels();
        _loadCommsTemplates();
      }
    });
  }

  async function _loadCatListForHeatmap() {
    try {
      const r = await fetch('/api/security/pets');
      if (!r.ok) return;
      const d = await r.json();
      const sel = $('heatmap-cat-select');
      if (!sel || !d.pets) return;
      const cur = sel.value;
      sel.innerHTML = '<option value="">Todos los gatos</option>';
      d.pets.forEach(p => {
        const o = document.createElement('option');
        o.value = p.id || p.name;
        o.textContent = p.name;
        sel.appendChild(o);
      });
      sel.value = cur;
    } catch {}
  }

  async function _loadCamsForRecFilter() {
    try {
      const r = await fetch('/api/cameras');
      if (!r.ok) return;
      const d = await r.json();
      const sel = $('rec-cam-filter');
      if (!sel || !d.cameras) return;
      const cur = sel.value;
      sel.innerHTML = '<option value="">Todas las cámaras</option>';
      d.cameras.forEach(cam => {
        const o = document.createElement('option');
        o.value = cam.name || cam.id;
        o.textContent = cam.name;
        sel.appendChild(o);
      });
      sel.value = cur;
    } catch {}
  }

  // ── Init ──────────────────────────────────────────────────────────────────
  setTTS(state.ttsOn);
  updateBrainBadge();
  setInterval(updateBrainBadge, 2000);
})();
// BATCH 4 EXTENSIONS — Deterrence / Actuators / HA Devices / Training Adv
// AY-01..08 / AT-05 / BA-01..06 / AE-05..10
(function() {
  'use strict';
  const $ = id => document.getElementById(id);

  function initDeterrence() {
    const loadBtn = $('deterr-load-btn');
    const camSel = $('deterr-cam-select');
    if (!loadBtn) return;

    fetch('/api/cameras').then(r => r.json()).then(d => {
      if (!camSel || !d.cameras) return;
      d.cameras.forEach(cam => {
        const o = document.createElement('option');
        o.value = cam.id || cam.name;
        o.textContent = cam.name || cam.id;
        camSel.appendChild(o);
      });
    }).catch(() => {});

    loadBtn.onclick = async () => {
      const camId = camSel.value;
      if (!camId) return;
      const r = await fetch('/api/security/deterrence/' + encodeURIComponent(camId));
      const d = await r.json();
      $('deterr-panel').style.display = '';
      const modeSel = $('deterr-mode-select');
      if (d.mode && modeSel) modeSel.value = d.mode;
      const info = $('deterr-state-info');
      if (info) info.textContent = 'Nivel: ' + d.level + ' | Activo: ' + (d.active ? 'Si' : 'No') + ' | Modo: ' + d.mode;
    };

    const modeBtn = $('deterr-mode-save');
    if (modeBtn) modeBtn.onclick = async () => {
      const camId = camSel.value;
      const mode = $('deterr-mode-select').value;
      await fetch('/api/security/deterrence/' + encodeURIComponent(camId) + '/mode', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ mode }),
      });
      const res = $('deterr-result');
      if (res) res.textContent = 'Modo guardado: ' + mode;
    };

    const fireBtn = $('deterr-fire-btn');
    if (fireBtn) fireBtn.onclick = async () => {
      const camId = camSel.value;
      const level = parseInt($('deterr-level-select').value);
      const r = await fetch('/api/security/deterrence/' + encodeURIComponent(camId) + '/trigger', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ level }),
      });
      const d = await r.json();
      const res = $('deterr-result');
      if (res) res.textContent = d.ok ? ('Nivel ' + level + ' disparado') : ('Error: ' + d.error);
    };

    const stopBtn = $('deterr-stop-btn');
    if (stopBtn) stopBtn.onclick = async () => {
      const camId = camSel.value;
      await fetch('/api/security/deterrence/' + encodeURIComponent(camId) + '/deescalate', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: '{}',
      });
      const res = $('deterr-result');
      if (res) res.textContent = 'Disuasion detenida';
    };
  }

  function initActuators() {
    const refreshBtn = $('actuators-refresh');
    if (!refreshBtn) return;

    async function loadActuators() {
      const r = await fetch('/api/actuators');
      const d = await r.json();
      const list = $('actuators-list');
      if (!list) return;
      if (!d.actuators || !d.actuators.length) {
        list.innerHTML = '<div class="comms-loading">Sin actuadores registrados</div>';
        return;
      }
      list.innerHTML = d.actuators.map(function(a) {
        return '<div class="actuator-row"><span class="actuator-name">' + a.name + '</span>' +
          '<span class="actuator-status ' + (a.available ? 'status-green' : 'status-red') + '">' +
          (a.available ? 'OK' : 'OFF') + '</span>' +
          '<button class="mini-btn" onclick="testActuator(\'' + a.name + '\')">Test</button></div>';
      }).join('');
    }

    refreshBtn.onclick = loadActuators;

    window.testActuator = async function(name) {
      const r = await fetch('/api/actuators/' + encodeURIComponent(name) + '/test', { method: 'POST' });
      const d = await r.json();
      alert('Test ' + name + ': ' + d.status + ' - ' + (d.evidence || ''));
    };

    const saveBtn = $('actuators-assign-save');
    if (saveBtn) saveBtn.onclick = async () => {
      const camId = $('actuators-cam-select').value;
      const checked = Array.from(document.querySelectorAll('.actuator-assign-check:checked')).map(c => c.value);
      await fetch('/api/actuators/assign', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ cam_id: camId, actuators: checked }),
      });
      const res = $('actuators-assign-result');
      if (res) res.textContent = 'Guardado';
    };

    loadActuators();
  }

  function initHADevices() {
    const discoverBtn = $('ha-discover-btn');
    if (!discoverBtn) return;

    discoverBtn.onclick = async () => {
      const domain = $('ha-domain-filter').value;
      const url = '/api/ha/entities' + (domain ? '?domain=' + domain : '');
      const r = await fetch(url);
      const d = await r.json();
      const list = $('ha-entities-list');
      if (!list) return;
      if (!d.entities || !d.entities.length) {
        list.innerHTML = '<div class="comms-loading">No se encontraron entidades HA</div>';
        return;
      }
      list.innerHTML = d.entities.map(function(e) {
        return '<div class="ha-entity-row">' +
          '<span class="ha-entity-id">' + e.entity_id + '</span>' +
          '<span class="ha-entity-name">' + e.name + '</span>' +
          '<span class="ha-entity-state">' + e.state + '</span>' +
          '<button class="mini-btn" onclick="addHAActuator(\'' + e.entity_id + '\',\'' + e.name + '\')">+ Anadir</button>' +
          '<button class="mini-btn" onclick="testHADevice(\'' + e.entity_id + '\')">Test</button>' +
          '</div>';
      }).join('');
    };

    window.addHAActuator = async function(entityId, name) {
      const r = await fetch('/api/ha/add-device', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ entity_id: entityId, label: name }),
      });
      const d = await r.json();
      alert(d.ok ? ('Anadido: ' + d.actuator) : ('Error: ' + d.error));
    };

    window.testHADevice = async function(entityId) {
      const r = await fetch('/api/ha/test-device', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ entity_id: entityId, action: 'toggle' }),
      });
      const d = await r.json();
      alert(d.ok ? (entityId + ' toggle OK') : ('Error: ' + d.error));
    };
  }

  function initTrainingAdv() {
    const versionsBtn = $('train-versions-load');
    const refreshJobBtn = $('train-refresh-job');
    if (!versionsBtn) return;

    versionsBtn.onclick = async () => {
      const modelId = $('train-model-select').value;
      const r = await fetch('/api/training/versions/' + encodeURIComponent(modelId));
      const d = await r.json();
      const list = $('train-versions-list');
      if (!list) return;
      if (!d.versions || !d.versions.length) {
        list.innerHTML = '<div class="comms-loading">Sin versiones registradas</div>';
        return;
      }
      list.innerHTML = d.versions.map(function(v) {
        return '<div class="train-version-row ' + (v.active ? 'train-version-active' : '') + '">' +
          '<span class="train-version-num">v' + v.version + '</span>' +
          '<span class="train-version-ts">' + new Date(v.ts).toLocaleString() + '</span>' +
          (v.active ? '<span class="train-badge-active">activa</span>' : '') +
          '<button class="mini-btn" onclick="promoteVersion(\'' + modelId + '\',' + v.version + ')">Promover</button>' +
          '</div>';
      }).join('') +
        '<div class="comms-row" style="margin-top:8px">' +
        '<button class="mini-btn" onclick="rollbackModel(\'' + modelId + '\')">Rollback</button></div>';
    };

    window.promoteVersion = async function(modelId, version) {
      const r = await fetch('/api/training/promote/' + encodeURIComponent(modelId), { method: 'POST' });
      const d = await r.json();
      alert(d.ok ? ('v' + version + ' promovida') : ('Error: ' + d.error));
      versionsBtn.click();
    };

    window.rollbackModel = async function(modelId) {
      const r = await fetch('/api/training/rollback/' + encodeURIComponent(modelId), { method: 'POST' });
      const d = await r.json();
      alert(d.ok ? ('Rollback a v' + d.rolled_back_to) : ('Error: ' + d.error));
      versionsBtn.click();
    };

    if (refreshJobBtn) refreshJobBtn.onclick = async () => {
      const r = await fetch('/api/training/stats');
      const stats = await r.json();
      const el = $('train-active-job');
      if (!el) return;
      if (stats.active_jobs && stats.active_jobs.length) {
        el.innerHTML = stats.active_jobs.map(function(j) {
          return '<div class="train-job-row"><span>' + j.job_id + '</span><span>' +
            j.model_id + '</span><span class="train-job-status">' + j.status + '</span></div>';
        }).join('');
      } else {
        el.innerHTML = '<div class="comms-loading">Sin trabajo activo</div>';
      }
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      initDeterrence();
      initActuators();
      initHADevices();
      initTrainingAdv();
    });
  } else {
    initDeterrence();
    initActuators();
    initHADevices();
    initTrainingAdv();
  }
})();
