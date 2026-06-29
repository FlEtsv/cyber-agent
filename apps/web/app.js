'use strict';

const TOOL_ICONS = {
  shell:'>', run_python:'py', write_file:'edit', read_file:'file',
  list_directory:'dir', web_fetch:'web', list_processes:'proc',
  screenshot:'screen', screenshot_pc:'screen', install_package:'install',
  uninstall_package:'remove', system_info:'info',
  mistral_consult:'ai',
};

const CATEGORY_ICONS = {
  core:'core', web:'web', files:'file', system:'sys', desktop:'desk',
  network:'net', forensics:'lab', encode:'enc', rag:'rag',
  council:'ai', self:'self', mobile:'mob', other:'tool',
};
const ALWAYS_ASK_TOOLS = new Set(['mistral_consult']);

function isAlwaysAskTool(name, meta = {}) {
  return ALWAYS_ASK_TOOLS.has(name) || meta.category === 'council';
}

// â”€â”€ Markdown renderer (via marked CDN) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function renderMd(text) {
  if (!text) return '';
  try {
    return sanitizeHtml(marked.parse(text, { breaks: true, gfm: true }));
  } catch {
    return escHtml(text);
  }
}
function sanitizeHtml(html) {
  const template = document.createElement('template');
  template.innerHTML = String(html);
  template.content.querySelectorAll('script,style,iframe,object,embed,link,meta').forEach(el => el.remove());
  template.content.querySelectorAll('*').forEach(el => {
    [...el.attributes].forEach(attr => {
      const name = attr.name.toLowerCase();
      const value = String(attr.value || '').trim().toLowerCase();
      if (name.startsWith('on') || value.startsWith('javascript:') || value.startsWith('data:text/html')) {
        el.removeAttribute(attr.name);
      }
    });
  });
  return template.innerHTML;
}
function escHtml(s) {
  return String(s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function redactReportValue(value) {
  const sensitiveKey = /(password|passwd|pwd|token|api[_-]?key|secret|authorization|cookie|session|jwt|bearer|credential|private[_-]?key)/i;
  const jwtRe = /eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g;
  const bearerRe = /\bBearer\s+[A-Za-z0-9._~+/-]+=*/gi;
  const inlineRe = /\b(access[_-]?token|refresh[_-]?token|client[_-]?secret|session[_-]?cookie|password|passwd|pwd|token|api[_-]?key|secret|authorization|cookie|totp[_-]?secret|host[_-]?secret)\b(\s*[:=]\s*)([^\s,;&]+)/gi;
  const queryRe = /([?&](?:access[_-]?token|refresh[_-]?token|client[_-]?secret|session[_-]?cookie|password|passwd|pwd|token|api[_-]?key|secret|authorization|cookie|jwt)=)([^&#]+)/gi;
  if (Array.isArray(value)) return value.map(redactReportValue);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).map(([key, val]) => [
      key,
      sensitiveKey.test(key) ? '[REDACTED]' : redactReportValue(val),
    ]));
  }
  if (typeof value === 'string') {
    return value
      .replace(jwtRe, '[JWT_REDACTED]')
      .replace(bearerRe, 'Bearer [REDACTED]')
      .replace(queryRe, '$1[REDACTED]')
      .replace(inlineRe, '$1$2[REDACTED]');
  }
  return value;
}

// â”€â”€ CyberAgent Web App â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class CyberAgent {
  constructor() {
    this.ws            = null;
    this.streaming     = false;
    this.attachedImgs  = [];
    this.toolRows      = new Map();
    this.currentBubble = null;
    this.pendingApproval = null;
    this.permissions   = {};
    this.sessionTrust  = false;
    this.selectedModel = '';
    this.sessionId     = '';
    this.availableModels = [];
    this.activeModel   = '';
    this.currentConversationId = '';
    this.conversations = [];
    this.outbox        = [];
    this.reconnectDelay = 1500;
    this.reconnectTimer = null;
    this.reconnectNoticeTimer = null;
    this.connectionBanner = null;
    this.pcOnline = true;
    this.queueBadge = null;
    this.settingsPanel = null;
    this.settingsBackdrop = null;
    this._watchContainer = null;
    this._watchFramesEl  = null;
    this._watchCounterEl = null;
    this.report = {
      startedAt: new Date().toISOString(),
      messages: [],
      tools: [],
      errors: [],
      status: [],
    };

    // Detect device type for server context
    const ua = navigator.userAgent.toLowerCase();
    this.isMobile = /android|iphone|ipad|mobile/.test(ua);
    this.platform = /android/.test(ua) ? 'Android'
                  : /iphone|ipad/.test(ua) ? 'iOS'
                  : /windows/.test(ua) ? 'Windows PC'
                  : /mac/.test(ua) ? 'macOS'
                  : 'PC';

    this.$ = id => document.getElementById(id);
    this.messages = document.getElementById('messages');
    this.inputEl  = document.getElementById('input');
    this.sendBtn  = document.getElementById('send-btn');
    this.stopBtn  = document.getElementById('stop-btn');
    this.attachEl = document.getElementById('attachments');
    this.approvalOverlay = document.getElementById('approval-overlay');
    this.statusDot  = document.querySelector('.status-dot');
    this.statusText = document.getElementById('status-text');
    this.conversationList = document.getElementById('conversation-list');
    this.activityList = document.getElementById('activity-list');

    this._loadPreferences();
    this._loadConversations();
    this._ensureConnectionBanner();
    this._ensureQueueBadge();
    this._initSettingsPanel();
    this._initBackground();
    this._installReportButton();
    this._initConversationPanel();
    this._bindUI();
    this._bindDragDrop();
    this._connect();
  }

  // â”€â”€ WebSocket â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  _connect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this._setConnectionState('offline', 'conectando...', 'Conectando con CyberAgent...', true);

    const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url   = `${proto}//${location.host}/ws`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectDelay = 1500;
      this._clearTransientConversationState();
      this._setConnectionState('', 'conectado');
      this._flushOutbox();
    };
    this.ws.onclose = e => {
      if (e.code === 4401) {
        window.location.href = '/login';
        return;
      }
      this._handleDisconnect('desconectado');
      const wait = this.reconnectDelay;
      this.reconnectDelay = Math.min(this.reconnectDelay * 1.7, 15000);
      this.reconnectTimer = setTimeout(() => this._connect(), wait);
    };
    this.ws.onerror = () => this._setConnectionState('error', 'error WS', 'Error de conexion con el relay.', true);
    this.ws.onmessage = e => {
      try {
        this._onMessage(JSON.parse(e.data));
      } catch {
        this._setStatus('error', 'evento invalido');
      }
    };
  }

  _send(obj) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
    } else {
      this.outbox.push(obj);
      this._handleDisconnect('reconectando...');
    }
  }

  _flushOutbox() {
    if (this.ws?.readyState !== WebSocket.OPEN) return;
    while (this.outbox.length) {
      this.ws.send(JSON.stringify(this.outbox.shift()));
    }
  }

  _preferredModelLabel(models = [], activeModel = '') {
    const list = Array.isArray(models) ? models : [];
    return activeModel ||
      list.find(m => /qwen3-14b/i.test(m)) ||
      list.find(m => /qwen/i.test(m)) ||
      list.find(m => m === 'cyberagent-original' || m === 'cyberagent-original:latest') ||
      list.find(m => /cyber/i.test(m)) ||
      list[0] ||
      '';
  }

  _setHeaderModel(models = [], activeModel = '') {
    const modelEl = document.querySelector('.header-model');
    if (!modelEl) return;
    modelEl.textContent = this._preferredModelLabel(models, activeModel);
  }

  // â”€â”€ Incoming events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  _onMessage(evt) {
    const { type, data } = evt;
    this._recordReportEvent(type, data);

    switch (type) {
      case 'connected':
        this.pcOnline = data?.pc_online !== false;
        this.sessionId = data?.session_id || '';
        this.availableModels = data?.models || [];
        this.activeModel = data?.active_model || '';
        this._syncModelSelect();
        if (!this.pcOnline) {
          this._setConnectionState('offline', 'PC offline', 'El PC principal no esta conectado al relay.', true);
        } else {
          this._setConnectionState('', 'conectado');
        }
        this._setHeaderModel(this.availableModels, this.activeModel);
        this._requestHistory();
        this._loadFolders();
        this._showWelcome();
        break;

      case 'workspace:result': {
        const cb = this._wsReq && this._wsReq[evt.req_id];
        if (cb) { delete this._wsReq[evt.req_id]; cb(evt); }
        break;
      }

      case 'models':
        this.availableModels = data?.models || [];
        this.activeModel = data?.active || data?.active_model || '';
        this._syncModelSelect();
        this._setHeaderModel(this.availableModels, this.activeModel);
        break;

      case 'history':
        this._restoreHistory(Array.isArray(data) ? data : []);
        break;

      case 'status':
        if (this._handleQueueStatus(data)) break;
        this._setStatus('thinking', data);
        this._renderActivity('estado', data);
        break;

      case 'reasoning':
        this._hideQueueBadge();
        // Exposición del consumo de Mistral en la web: el host emite
        // "Consumo Mistral (sesión): $X · N llamadas" al terminar cada tarea.
        if (typeof data === 'string' && data.indexOf('Consumo Mistral') !== -1) {
          const b = this.$('cost-badge');
          if (b) {
            b.textContent = '💸 ' + data.replace(/^.*?:\s*/, '').split('·').slice(0, 2).join('·').trim();
            b.hidden = false;
          }
        }
        this._appendReasoning(data);
        break;

      case 'savings': {
        const sb = this.$('savings-badge');
        if (sb && data && typeof data.total_saved === 'number') {
          sb.textContent = '💰 $' + data.total_saved.toFixed(2);
          sb.title = `Ahorrado con el modelo local: $${data.total_saved.toFixed(4)} en total · ${(data.total_tokens || 0).toLocaleString()} tokens gratis`;
          sb.hidden = false;
        }
        break;
      }

      case 'token':
        this._hideQueueBadge();
        this._ensureAIBubble();
        this.currentBubble._raw += data;
        this._renderCurrentBubble();
        this._scrollBottom();
        break;

      case 'tool_call':
        this._ensureAIBubble();
        this._addToolActivity(data.id, data.name, data.args, data);
        this._renderActivity('herramienta', data?.name || 'tool_call');
        break;

      case 'need_approval':
        this._showApproval(data.id, data.name, data.args, data);
        this._renderActivity('aprobacion', data?.name || 'herramienta');
        break;

      case 'tool_result':
        this._setToolDone(data.id, data.result ?? data.output ?? data.content ?? data);
        this._renderActivity('resultado', data?.name || data?.id || 'tool_result');
        break;

      case 'vision_processing':
        this._setStatus('thinking', data);
        this._renderActivity('vision', data);
        break;

      case 'screenshot':
        this._handleWatchFrame(data);
        break;

      case 'watch_ended':
        this._endWatchMode(data?.frames ?? 0);
        break;

      case 'done':
        this._hideQueueBadge();
        this._finalizeAIBubble();
        this._renderActivity('respuesta', 'completada');
        this._endStreaming();
        break;

      case 'error':
        if (typeof data === 'string' && /pc no conectado|pc no est/i.test(data)) {
          this.pcOnline = false;
          this._setConnectionState('offline', 'PC offline', data, true);
        }
        this._addErrorMsg(data);
        this._renderActivity('error', data);
        this._endStreaming();
        break;
    }
  }

  // ── GPU queue badge ────────────────────────────────────────────────────────

  _ensureQueueBadge() {
    this.queueBadge = document.getElementById('queue-badge');
    if (this.queueBadge) return;
    const header = document.querySelector('header');
    if (!header) return;
    this.queueBadge = document.createElement('span');
    this.queueBadge.id = 'queue-badge';
    this.queueBadge.hidden = true;
    header.appendChild(this.queueBadge);
  }

  _handleQueueStatus(data) {
    if (typeof data !== 'string' || !/GPU ocupada|posici[oó]n\s+\d/i.test(data)) return false;
    const pos = data.match(/posici[oó]n\s+(\d+)/i)?.[1] || '';
    this._ensureQueueBadge();
    if (this.queueBadge) {
      this.queueBadge.textContent = pos ? `Cola #${pos}` : 'Cola GPU';
      this.queueBadge.hidden = false;
    }
    this._setStatus('thinking', pos ? `cola GPU #${pos}` : 'cola GPU');
    return true;
  }

  _hideQueueBadge() {
    this._ensureQueueBadge();
    if (this.queueBadge) this.queueBadge.hidden = true;
  }

  // ── Watch mode ─────────────────────────────────────────────────────────────

  _handleWatchFrame(data) {
    if (!this._watchContainer) {
      const wrap = document.createElement('div');
      wrap.className = 'msg watch-mode';
      wrap.innerHTML = `
        <div class="watch-header">
          <span class="watch-icon">cam</span>
          <span class="watch-label">Modo Vigilancia</span>
          <button class="watch-stop-btn" title="Detener vigilancia">Stop</button>
          <span class="watch-counter">0 capturas</span>
        </div>
        <div class="watch-frames"></div>
      `;
      wrap.querySelector('.watch-stop-btn').addEventListener('click', () => {
        this._send({ type: 'watch_stop' });
      });
      this._watchContainer = wrap;
      this._watchFramesEl = wrap.querySelector('.watch-frames');
      this._watchCounterEl = wrap.querySelector('.watch-counter');
      this._removeWelcome();
      this.messages.appendChild(wrap);
    }

    const { b64, fmt, size, seq, elapsed, duration } = data || {};
    if (!b64 || !this._watchFramesEl) return;
    const img = document.createElement('img');
    img.src = `data:image/${fmt || 'jpeg'};base64,${b64}`;
    img.className = 'watch-frame';
    img.title = `#${(seq || 0) + 1} - ${size || ''} - +${elapsed || 0}s`;
    img.loading = 'lazy';

    this._watchFramesEl.appendChild(img);
    const frames = this._watchFramesEl.querySelectorAll('.watch-frame');
    if (frames.length > 6) frames[0].remove();

    const count = (seq || 0) + 1;
    const pct = duration ? Math.min(100, Math.round((elapsed || 0) / duration * 100)) : 0;
    if (this._watchCounterEl) {
      this._watchCounterEl.textContent = `${count} captura${count !== 1 ? 's' : ''} - ${pct}%`;
    }
    this._scrollBottom();
  }

  _endWatchMode(frames) {
    if (!this._watchContainer) return;
    const hdr = this._watchContainer.querySelector('.watch-header');
    if (hdr) {
      hdr.querySelector('.watch-stop-btn')?.remove();
      const lbl = hdr.querySelector('.watch-label');
      if (lbl) lbl.textContent = 'Vigilancia finalizada';
      const ctr = hdr.querySelector('.watch-counter');
      if (ctr) ctr.textContent = `${frames} capturas`;
    }
    this._watchContainer = null;
    this._watchFramesEl = null;
    this._watchCounterEl = null;
  }

  // â”€â”€ Send message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  send() {
    const text = this.inputEl.value.trim();
    if ((!text && this.attachedImgs.length === 0) || this.streaming) return;
    if (this.ws?.readyState !== WebSocket.OPEN || !this.pcOnline) {
      this._setConnectionState('offline', this.pcOnline ? 'reconectando...' : 'PC offline',
        this.pcOnline ? 'Esperando reconexion con el relay.' : 'El PC principal no esta conectado al relay.', true);
      return;
    }

    // Contexto previo (antes de añadir el mensaje actual): así el PC recuerda la
    // conversación aunque el móvil se reconecte (nuevo session_id) o el host reinicie.
    const priorHistory = this._historyForRelay();

    this._beginStreaming();
    this._addUserBubble(text, this.attachedImgs.map(i => i.dataUrl));

    this._send({
      type:          'message',
      content:       text,
      history:       priorHistory,
      images:        this.attachedImgs.map(i => i.b64),
      session_trust: this.sessionTrust,
      permissions:   this.permissions,
      model:         this.selectedModel || undefined,
      folder_id:     this._currentFolderId() || undefined,
      device:        `${this.isMobile ? 'movil' : 'PC'} ${this.platform}`,
    });

    this.inputEl.value = '';
    this._resetAttachments();
    this._autoResize();
  }

  stop() {
    this._send({ type: 'stop' });
  }

  // â”€â”€ UI: message bubbles â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  _addUserBubble(text, imageSrcs = [], opts = {}) {
    if (!opts.restored) {
      this.report.messages.push({
        ts: new Date().toISOString(),
        role: 'user',
        text: redactReportValue(text),
        images: imageSrcs.length,
      });
      this._persistHistoryMessage({ role: 'user', text, images: imageSrcs, ts: Date.now() });
      this._touchConversation(text);
    }
    const wrap = document.createElement('div');
    wrap.className = `msg user${opts.restored ? ' restored' : ''}`;

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = 'TU';

    const body = document.createElement('div');
    body.className = 'msg-body';

    if (imageSrcs.length) {
      const imgRow = document.createElement('div');
      imgRow.className = 'msg-images';
      imageSrcs.forEach(src => {
        const img = document.createElement('img');
        img.src = src;
        imgRow.appendChild(img);
      });
      body.appendChild(imgRow);
    }

    if (text) {
      const content = document.createElement('div');
      content.className = 'msg-content';
      content.innerHTML = renderMd(text);
      body.appendChild(content);
    }

    wrap.appendChild(avatar);
    wrap.appendChild(body);
    this._removeWelcome();
    this.messages.appendChild(wrap);
    this._scrollBottom();
  }

  _ensureAIBubble() {
    if (this.currentBubble) return;

    const wrap = document.createElement('div');
    wrap.className = 'msg ai';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = 'AI';

    const body = document.createElement('div');
    body.className = 'msg-body';

    // Reasoning / proceso (separado y atenuado, encima de la respuesta final)
    const reasoningSection = document.createElement('div');
    reasoningSection.className = 'reasoning-section';
    reasoningSection.style.display = 'none';

    const rToggle = document.createElement('button');
    rToggle.className = 'reasoning-toggle open';
    rToggle.innerHTML = '<span class="r-dot"></span><span class="r-label">Razonando…</span>';

    const rStream = document.createElement('div');
    rStream.className = 'reasoning-stream';

    rToggle.addEventListener('click', () => {
      const collapsed = rStream.classList.toggle('collapsed');
      rToggle.classList.toggle('open', !collapsed);
    });

    reasoningSection.appendChild(rToggle);
    reasoningSection.appendChild(rStream);
    body.appendChild(reasoningSection);

    const contentEl = document.createElement('div');
    contentEl.className = 'msg-content';
    // El contenido del mensaje se añade DEBAJO de las acciones (ver más abajo),
    // así el auto-scroll deja a la vista la respuesta final, no las acciones.

    // Actions section (collapsible)
    const actionsSection = document.createElement('div');
    actionsSection.className = 'actions-section';
    actionsSection.style.display = 'none';

    const toggle = document.createElement('button');
    toggle.className = 'actions-toggle';
    toggle.textContent = 'v  0 acciones';
    toggle.classList.add('open');

    const actionsList = document.createElement('div');
    actionsList.className = 'actions-list';

    toggle.addEventListener('click', () => {
      const hidden = actionsList.classList.toggle('hidden');
      const open = !hidden;
      toggle.textContent = (open ? 'v' : '>') + toggle.textContent.slice(1);
      toggle.classList.toggle('open', open);
    });

    actionsSection.appendChild(toggle);
    actionsSection.appendChild(actionsList);
    body.appendChild(actionsSection);

    // La respuesta final va DEBAJO de sus acciones correspondientes.
    body.appendChild(contentEl);

    wrap.appendChild(avatar);
    wrap.appendChild(body);
    this.messages.appendChild(wrap);

    this.currentBubble = {
      el: wrap,
      contentEl,
      reasoningSection,
      rStream,
      rToggle,
      actionsSection,
      actionsList,
      toggle,
      _raw: '',
      _reasoning: '',
      _count: 0,
    };

    this._scrollBottom();
  }

  _appendReasoning(text) {
    if (text === undefined || text === null) return;
    const chunk = typeof text === 'string' ? text : JSON.stringify(text);
    this._ensureAIBubble();
    const b = this.currentBubble;
    // separa pasos con salto de línea si llegan como mensajes de estado
    b._reasoning += (b._reasoning && !b._reasoning.endsWith('\n') ? '\n' : '') + chunk;
    b.reasoningSection.style.display = '';
    b.rStream.classList.remove('collapsed');
    b.rToggle.classList.add('open');
    b.rStream.textContent = b._reasoning;
    b.rStream.scrollTop = b.rStream.scrollHeight;
    this._setStatus('thinking', chunk.slice(0, 80));
    this._renderActivity('razonamiento', chunk.slice(0, 120));
    this._scrollBottom();
  }

  _renderCurrentBubble() {
    if (!this.currentBubble) return;
    this.currentBubble.contentEl.innerHTML = renderMd(this.currentBubble._raw);
  }

  _finalizeAIBubble() {
    if (!this.currentBubble) return;
    this._renderCurrentBubble();
    // Colapsa el razonamiento al terminar para que destaque la respuesta final
    if (this.currentBubble._reasoning) {
      this.currentBubble.rStream.classList.add('collapsed');
      this.currentBubble.rToggle.classList.remove('open');
      const lbl = this.currentBubble.rToggle.querySelector('.r-label');
      if (lbl) lbl.textContent = 'Ver razonamiento';
    } else if (this.currentBubble.reasoningSection) {
      this.currentBubble.reasoningSection.style.display = 'none';
    }
    this.report.messages.push({
      ts: new Date().toISOString(),
      role: 'assistant',
      text: redactReportValue(this.currentBubble._raw),
    });
    this._persistHistoryMessage({ role: 'assistant', text: this.currentBubble._raw, ts: Date.now() });
    this._touchConversation(this.currentBubble._raw, 'assistant');
    this.currentBubble = null;
  }

  _addRestoredAIBubble(text) {
    if (!text) return;
    const wrap = document.createElement('div');
    wrap.className = 'msg ai restored';

    const avatar = document.createElement('div');
    avatar.className = 'msg-avatar';
    avatar.textContent = 'AI';

    const body = document.createElement('div');
    body.className = 'msg-body';

    const contentEl = document.createElement('div');
    contentEl.className = 'msg-content';
    contentEl.innerHTML = renderMd(text);
    body.appendChild(contentEl);

    wrap.appendChild(avatar);
    wrap.appendChild(body);
    this._removeWelcome();
    this.messages.appendChild(wrap);
  }

  // ── Workspace: carpetas sincronizadas con el backend (protocolo workspace:*) ──
  _workspace(action, payload = {}) {
    return new Promise((resolve) => {
      const req_id = 'ws_' + Math.random().toString(36).slice(2, 10);
      this._wsReq = this._wsReq || {};
      this._wsReq[req_id] = resolve;
      this._send({ type: 'workspace:' + action, req_id, ...payload });
      setTimeout(() => {
        if (this._wsReq && this._wsReq[req_id]) { delete this._wsReq[req_id]; resolve({ error: 'timeout' }); }
      }, 12000);
    });
  }

  async _loadFolders() {
    const r = await this._workspace('get');
    if (Array.isArray(r.folders)) { this.folders = r.folders; this._renderConversationList(); }
  }

  _folderById(id) { return (this.folders || []).find(f => String(f.id) === String(id)); }

  _currentFolderId() {
    const c = (this.conversations || []).find(x => x.id === this.currentConversationId);
    return c ? (c.folderId || null) : null;
  }

  // A6: modal y menú sobrios (reemplazan prompt/confirm)
  _modal({ title, fields = [], submitLabel = 'Guardar', danger = false }) {
    return new Promise((resolve) => {
      const back = document.createElement('div');
      back.className = 'modal-backdrop';
      const box = document.createElement('div');
      box.className = 'modal-box';
      box.innerHTML = `<div class="modal-title">${escHtml(title)}</div>`;
      const body = document.createElement('div'); body.className = 'modal-body';
      const inputs = {};
      for (const f of fields) {
        const row = document.createElement('label'); row.className = 'modal-field';
        row.innerHTML = `<span>${escHtml(f.label)}</span>`;
        let input;
        if (f.type === 'select') {
          input = document.createElement('select');
          (f.options || []).forEach(o => {
            const op = document.createElement('option'); op.value = o.value; op.textContent = o.label;
            input.appendChild(op);
          });
          if (f.value != null) input.value = String(f.value);
        } else if (f.type === 'textarea') {
          input = document.createElement('textarea'); input.rows = 3;
          if (f.value) input.value = f.value;
        } else {
          input = document.createElement('input'); input.type = f.type || 'text';
          if (f.value != null) input.value = f.value;
          if (f.placeholder) input.placeholder = f.placeholder;
        }
        input.className = 'modal-input';
        inputs[f.name] = input; row.appendChild(input); body.appendChild(row);
      }
      box.appendChild(body);
      const btns = document.createElement('div'); btns.className = 'modal-btns';
      const cancel = document.createElement('button'); cancel.className = 'modal-btn'; cancel.textContent = 'Cancelar';
      const ok = document.createElement('button'); ok.className = 'modal-btn primary' + (danger ? ' danger' : ''); ok.textContent = submitLabel;
      btns.appendChild(cancel); btns.appendChild(ok); box.appendChild(btns);
      back.appendChild(box); document.body.appendChild(back);
      requestAnimationFrame(() => back.classList.add('open'));
      const close = (v) => { back.classList.remove('open'); setTimeout(() => back.remove(), 180); resolve(v); };
      cancel.onclick = () => close(null);
      back.onclick = (e) => { if (e.target === back) close(null); };
      ok.onclick = () => { const out = {}; for (const k in inputs) out[k] = inputs[k].value; close(out); };
      const first = body.querySelector('input,textarea,select'); if (first) setTimeout(() => first.focus(), 60);
    });
  }

  _menu(title, items) {
    return new Promise((resolve) => {
      const back = document.createElement('div'); back.className = 'modal-backdrop';
      const box = document.createElement('div'); box.className = 'modal-box menu';
      if (title) box.innerHTML = `<div class="modal-title">${escHtml(title)}</div>`;
      const list = document.createElement('div'); list.className = 'menu-list';
      const close = (v) => { back.classList.remove('open'); setTimeout(() => back.remove(), 180); resolve(v); };
      items.forEach(it => {
        const b = document.createElement('button');
        b.className = 'menu-item' + (it.danger ? ' danger' : '');
        b.textContent = it.label; b.onclick = () => close(it.value);
        list.appendChild(b);
      });
      box.appendChild(list); back.appendChild(box); document.body.appendChild(back);
      requestAnimationFrame(() => back.classList.add('open'));
      back.onclick = (e) => { if (e.target === back) close(null); };
    });
  }

  _modelOptions() {
    const opts = [{ value: '', label: '(heredar / auto)' }];
    (this.availableModels || []).forEach(m => opts.push({ value: m, label: m.replace(/:latest$/, '') }));
    ['codestral-latest', 'mistral-medium-latest', 'mistral-large-latest'].forEach(m => {
      if (!opts.find(o => o.value === m)) opts.push({ value: m, label: m });
    });
    return opts;
  }

  async _createFolder() {
    const r = await this._modal({ title: 'Nueva categoría', submitLabel: 'Crear', fields: [
      { name: 'name', label: 'Nombre', placeholder: 'Ingeniería' },
      { name: 'context', label: 'Contexto (opcional)', type: 'textarea', placeholder: 'Eres un ingeniero senior…' },
      { name: 'color', label: 'Color', type: 'color', value: '#54c7d8' },
      { name: 'default_model', label: 'Modelo por defecto', type: 'select', options: this._modelOptions() },
    ]});
    if (!r || !r.name.trim()) return null;
    const res = await this._workspace('folder_create', {
      name: r.name.trim(), context: r.context || '', color: r.color, default_model: r.default_model || null });
    if (res.error) { this._menu('Error: ' + res.error, [{ label: 'OK', value: 1 }]); return null; }
    await this._loadFolders();
    return res.id || null;
  }

  async _pickFolder(title = '¿Para quién es este chat?') {
    const items = [{ label: '📂 Sin carpeta', value: '__none__' },
      ...(this.folders || []).map(f => ({ label: '📁 ' + f.name, value: f.id })),
      { label: '＋ Nueva categoría…', value: '__new__' }];
    const choice = await this._menu(title, items);
    if (choice === null) return undefined;
    if (choice === '__none__') return null;
    if (choice === '__new__') return await this._createFolder();
    return choice;
  }

  async _convMenu(convId) {
    const conv = this.conversations.find(c => c.id === convId);
    if (!conv) return;
    const act = await this._menu('Conversación', [
      { label: '📁 Mover a carpeta', value: 'move' },
      { label: '🎨 Color', value: 'color' },
      { label: '🗑 Borrar', value: 'del', danger: true },
    ]);
    if (act === 'move') {
      const fid = await this._pickFolder('Mover a:');
      if (fid === undefined) return;
      conv.folderId = (typeof fid === 'number') ? fid : null;
    } else if (act === 'color') {
      const r = await this._modal({ title: 'Color de la conversación', submitLabel: 'Aplicar',
        fields: [{ name: 'color', label: 'Color', type: 'color', value: conv.color || '#54c7d8' }] });
      if (!r) return;
      conv.color = r.color || null;
    } else if (act === 'del') {
      const ok = await this._menu('¿Borrar esta conversación?', [
        { label: 'Sí, borrar', value: 'yes', danger: true }, { label: 'Cancelar', value: 'no' }]);
      if (ok !== 'yes') return;
      this.conversations = this.conversations.filter(c => c.id !== convId);
      if (this.currentConversationId === convId) {
        this.currentConversationId = (this.conversations[0] || {}).id || null;
        this._clearConversationView(); this._showWelcome();
      }
    } else { return; }
    this._saveConversations();
    this._renderConversationList();
  }

  async _editFolder(fid) {
    const f = this._folderById(fid);
    if (!f) return;
    const act = await this._menu(`Carpeta «${f.name}»`, [
      { label: '✏️ Editar', value: 'edit' },
      { label: '🗑 Borrar carpeta', value: 'del', danger: true },
    ]);
    if (act === 'edit') {
      const r = await this._modal({ title: 'Editar categoría', fields: [
        { name: 'name', label: 'Nombre', value: f.name },
        { name: 'context', label: 'Contexto', type: 'textarea', value: f.context || '' },
        { name: 'color', label: 'Color', type: 'color', value: f.color || '#54c7d8' },
        { name: 'default_model', label: 'Modelo por defecto', type: 'select', options: this._modelOptions(), value: f.default_model || '' },
      ]});
      if (!r) return;
      await this._workspace('folder_update', {
        id: f.id, name: r.name, context: r.context, color: r.color, default_model: r.default_model || null });
    } else if (act === 'del') {
      await this._workspace('folder_delete', { id: f.id });
    } else { return; }
    await this._loadFolders();
  }

  // ── A7: fondo de chat personalizado (color o imagen), persistente ──
  _bgKey() { return `ca_bg_${location.host}`; }
  _initBackground() {
    try { this._applyBackground(JSON.parse(localStorage.getItem(this._bgKey()) || 'null')); } catch {}
    const color = this.$('bg-color'), img = this.$('bg-image'), clr = this.$('bg-clear');
    if (color) color.addEventListener('input', () => this._setBackground({ type: 'color', value: color.value }));
    if (img) img.addEventListener('change', e => {
      const f = e.target.files && e.target.files[0];
      if (!f) return;
      const rd = new FileReader();
      rd.onload = ev => this._setBackground({ type: 'image', value: ev.target.result });
      rd.readAsDataURL(f);
    });
    if (clr) clr.addEventListener('click', () => this._setBackground(null));
  }
  _setBackground(bg) {
    try { localStorage.setItem(this._bgKey(), JSON.stringify(bg)); } catch {}
    this._applyBackground(bg);
  }
  _applyBackground(bg) {
    const el = this.messages;
    if (!el) return;
    if (!bg) { el.style.background = ''; return; }
    if (bg.type === 'color') el.style.background = bg.value;
    else if (bg.type === 'image') el.style.background = `center/cover no-repeat fixed url("${bg.value}")`;
  }

  _conversationsKey() {
    return `ca_conversations_${location.host}`;
  }

  _loadConversations() {
    try {
      const raw = localStorage.getItem(this._conversationsKey());
      this.conversations = raw ? JSON.parse(raw) : [];
      if (!Array.isArray(this.conversations)) this.conversations = [];
    } catch {
      this.conversations = [];
    }
    if (!this.conversations.length) {
      this.conversations = [{
        id: `chat_${Date.now()}`,
        title: 'Nuevo chat',
        updatedAt: Date.now(),
        count: 0,
      }];
    }
    this.currentConversationId = this.conversations[0].id;
    this._saveConversations();
  }

  _saveConversations() {
    localStorage.setItem(this._conversationsKey(), JSON.stringify(this.conversations.slice(0, 30)));
  }

  _initConversationPanel() {
    this._collapsed = this._collapsed || {};
    this.$('new-chat-btn')?.addEventListener('click', () => this._newConversation());
    this.$('new-folder-btn')?.addEventListener('click', () => this._createFolder());
    this.conversationList?.addEventListener('click', e => {
      const menu = e.target.closest?.('[data-conv-menu]');
      if (menu) { e.stopPropagation(); this._convMenu(menu.dataset.convMenu); return; }
      const fedit = e.target.closest?.('[data-folder-edit]');
      if (fedit) { e.stopPropagation(); this._editFolder(fedit.dataset.folderEdit); return; }
      const ftog = e.target.closest?.('[data-folder-toggle]');
      if (ftog) { this._collapsed[ftog.dataset.folderToggle] = !this._collapsed[ftog.dataset.folderToggle]; this._renderConversationList(); return; }
      const button = e.target.closest?.('[data-conversation-id]');
      if (button) this._switchConversation(button.dataset.conversationId);
    });
    this._renderConversationList();
    this._renderActivity('system', 'Web lista');
  }

  async _newConversation() {
    const folderId = await this._pickFolder();   // "¿para quién es?"
    if (folderId === undefined) return;          // cancelado
    this.currentConversationId = `chat_${Date.now()}`;
    this.conversations.unshift({
      id: this.currentConversationId,
      title: 'Nuevo chat',
      updatedAt: Date.now(),
      count: 0,
      folderId: folderId || null,
    });
    this._saveConversations();
    this._clearConversationView();
    this._renderConversationList();
    this._showWelcome();
  }

  _switchConversation(id) {
    if (!id || id === this.currentConversationId) return;
    this.currentConversationId = id;
    this._clearConversationView();
    this._restoreHistory(this._loadLocalHistory(), { force: true });
    this._renderConversationList();
    this._showWelcome();
  }

  _clearConversationView() {
    this.toolRows.clear();
    this.currentBubble = null;
    this._hideApproval();
    this.messages.innerHTML = '';
  }

  _touchConversation(text = '', role = 'user') {
    let conv = this.conversations.find(item => item.id === this.currentConversationId);
    if (!conv) {
      conv = { id: this.currentConversationId || `chat_${Date.now()}`, title: 'Nuevo chat', updatedAt: Date.now(), count: 0 };
      this.currentConversationId = conv.id;
      this.conversations.unshift(conv);
    }
    const clean = String(text || '').replace(/\s+/g, ' ').trim();
    if (role === 'user' && clean && (!conv.title || conv.title === 'Nuevo chat')) {
      conv.title = clean.slice(0, 58);
    }
    conv.updatedAt = Date.now();
    conv.count = (conv.count || 0) + 1;
    this.conversations = [conv, ...this.conversations.filter(item => item.id !== conv.id)]
      .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));
    this._saveConversations();
    this._renderConversationList();
  }

  _renderConversationList() {
    if (!this.conversationList) return;
    this.conversationList.innerHTML = '';
    this._collapsed = this._collapsed || {};
    const convs = this.conversations.slice(0, 60);
    const folders = this.folders || [];

    const renderConv = (conv) => {
      const item = document.createElement('button');
      item.className = `conversation-item${conv.id === this.currentConversationId ? ' active' : ''}`;
      item.dataset.conversationId = conv.id;
      if (conv.color) item.style.borderLeft = `3px solid ${conv.color}`;
      const title = document.createElement('div');
      title.className = 'conversation-title';
      title.textContent = conv.title || 'Nuevo chat';
      const meta = document.createElement('div');
      meta.className = 'conversation-meta';
      meta.textContent = `${conv.count || 0} eventos · ${this._formatTime(conv.updatedAt)}`;
      const m = document.createElement('span');
      m.className = 'conv-menu-btn';
      m.textContent = '⋯';
      m.dataset.convMenu = conv.id;
      item.appendChild(title); item.appendChild(meta); item.appendChild(m);
      this.conversationList.appendChild(item);
    };

    const groups = new Map();
    for (const c of convs) {
      const k = (c.folderId != null) ? String(c.folderId) : '';
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(c);
    }

    const renderFolder = (f, depth = 0) => {
      const k = String(f.id);
      const open = !this._collapsed[k];
      const h = document.createElement('div');
      h.className = 'folder-header';
      h.style.paddingLeft = `${8 + depth * 12}px`;
      h.dataset.folderToggle = k;
      h.innerHTML =
        `<span class="folder-caret">${open ? '▾' : '▸'}</span>` +
        `<span class="folder-dot" style="background:${f.color || 'var(--dim)'}"></span>` +
        `<span class="folder-name">${escHtml(f.name)}</span>` +
        `<span class="folder-count">${(groups.get(k) || []).length || ''}</span>` +
        `<span class="folder-edit" data-folder-edit="${k}">⚙</span>`;
      this.conversationList.appendChild(h);
      if (open) (groups.get(k) || []).forEach(renderConv);
    };

    folders.filter(f => !f.parent_id).forEach(f => {
      renderFolder(f, 0);
      folders.filter(s => String(s.parent_id) === String(f.id)).forEach(s => renderFolder(s, 1));
    });

    const loose = groups.get('') || [];
    if (loose.length) {
      if (folders.length) {
        const h = document.createElement('div');
        h.className = 'folder-header';
        h.innerHTML = `<span class="folder-caret"></span><span class="folder-name dim">Sin carpeta</span>`;
        this.conversationList.appendChild(h);
      }
      loose.forEach(renderConv);
    }
  }

  _renderActivity(kind, text) {
    if (!this.activityList) return;
    const item = document.createElement('div');
    item.className = 'activity-item';
    item.innerHTML = `<strong>${escHtml(kind)}</strong><br>${escHtml(String(text || '').slice(0, 180))}<div class="activity-meta">${this._formatTime(Date.now())}</div>`;
    this.activityList.prepend(item);
    while (this.activityList.children.length > 20) {
      this.activityList.lastElementChild.remove();
    }
  }

  _formatTime(ts) {
    if (!ts) return '';
    try {
      return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  }

  _historyKey() {
    return `ca_history_${location.host}_${this.currentConversationId || 'default'}`;
  }

  _loadLocalHistory() {
    try {
      const raw = localStorage.getItem(this._historyKey());
      const parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  _historyForRelay() {
    // Historial reciente en formato {role, content} para dar contexto al PC.
    try {
      return this._loadLocalHistory()
        .filter(m => (m.role === 'user' || m.role === 'assistant') && m.text)
        .slice(-20)
        .map(m => ({ role: m.role, content: String(m.text).slice(0, 4000) }));
    } catch { return []; }
  }

  _persistHistoryMessage(message) {
    const history = this._loadLocalHistory();
    history.push(message);
    localStorage.setItem(this._historyKey(), JSON.stringify(history.slice(-50)));
  }

  async _requestHistory() {
    // Fuente ÚNICA de verdad: el historial local de ESTA conversación.
    // El buffer del relay es por-sesión (no sabe de conversaciones), así que
    // mezclaba/duplicaba la respuesta al reconectar. Ya no lo usamos para mostrar.
    if (this.messages.querySelector('.msg.restored, .msg.user, .msg.ai')) return;
    this._restoreHistory(this._loadLocalHistory());
  }

  _restoreHistory(messages, opts = {}) {
    if (!Array.isArray(messages) || !messages.length) return;
    if (!opts.force && this.messages.querySelector('.msg.restored')) return;
    let assistantText = '';
    let restored = 0;

    const flushAssistant = () => {
      if (!assistantText.trim()) return;
      this._addRestoredAIBubble(assistantText);
      assistantText = '';
      restored++;
    };

    for (const item of messages.slice(-50)) {
      const type = item?.type;
      const role = item?.role;
      if (role === 'user' || type === 'user_message') {
        flushAssistant();
        this._addUserBubble(item.text || item.content || '', item.images || [], { restored: true });
        restored++;
      } else if (role === 'assistant') {
        flushAssistant();
        this._addRestoredAIBubble(item.text || item.content || '');
        restored++;
      } else if (type === 'token') {
        assistantText += item.data || '';
      } else if (type === 'done') {
        flushAssistant();
      } else if (type === 'error') {
        flushAssistant();
        this._addRestoredAIBubble(`Error anterior: ${item.data || item.error || ''}`);
        restored++;
      }
    }
    flushAssistant();
    if (restored) {
      this._removeWelcome();
      this._scrollBottom();
    }
  }

  _addErrorMsg(msg) {
    this.report.errors.push({ ts: new Date().toISOString(), message: redactReportValue(String(msg)) });
    this.toolRows.clear();
    this._ensureAIBubble();
    this.currentBubble.contentEl.textContent = msg;
    this.currentBubble.el.classList.add('error');
    this.currentBubble = null;
  }

  // â”€â”€ Tool activity â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  _addToolActivity(id, name, args, meta = {}) {
    if (!this.currentBubble) return;
    const { actionsSection, actionsList, toggle } = this.currentBubble;

    const icon = TOOL_ICONS[name] || 'tool';
    const category = meta.category || 'tool';
    const categoryIcon = CATEGORY_ICONS[category] || 'tool';
    const argsPreview = Object.entries(args || {})
      .map(([k,v]) => `${k}=${JSON.stringify(v).slice(0,30)}`)
      .join('  ').slice(0, 60);

    const row = document.createElement('div');
    row.className = 'tool-row';
    row.innerHTML = `
      <span class="tool-row-name">${icon}  ${escHtml(name)}</span>
      <span class="tool-row-meta ${meta.risk === 'high' ? 'high' : 'low'}">${escHtml(categoryIcon)} · ${escHtml(category)} · ${escHtml(meta.risk || 'low')}</span>
      <span class="tool-row-args">${escHtml(argsPreview)}</span>
      <span class="tool-row-status pending">...</span>
    `;

    actionsList.appendChild(row);
    actionsSection.style.display = '';
    this.currentBubble._count++;
    const n = this.currentBubble._count;
    toggle.textContent = `v  ${n} ${n === 1 ? 'accion' : 'acciones'}`;
    toggle.classList.add('open');
    actionsList.classList.remove('hidden');

    this.toolRows.set(id, { row, status: row.querySelector('.tool-row-status') });
    this.report.tools.push({
      ts: new Date().toISOString(),
      id,
      name,
      category: meta.category || 'tool',
      risk: meta.risk || 'low',
      args: redactReportValue(args),
      status: 'pending',
    });
    this._scrollBottom();
  }

  _setToolDone(id, result = null) {
    const t = this.toolRows.get(id);
    if (!t) return;
    t.status.textContent = 'done';
    t.status.className   = 'tool-row-status done';
    this._updateReportTool(id, 'done', result);
    if (result === null || t.row.querySelector('.tool-row-result, .tool-row-diff, .tool-row-todos')) return;
    // Si la herramienta devolvió un diff (edit_file), píntalo rojo/verde como Claude Code.
    if (result && typeof result === 'object' && typeof result.diff === 'string' && result.diff.trim()) {
      t.row.appendChild(this._renderDiff(result));
      return;
    }
    // Lista de tareas (todo_write) → checklist visible.
    if (result && typeof result === 'object' && Array.isArray(result.todos)) {
      t.row.appendChild(this._renderTodos(result.todos));
      return;
    }
    const pre = document.createElement('pre');
    pre.className = 'tool-row-result';
    const text = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
    pre.textContent = text.length > 3000 ? text.slice(0, 3000) + '\n... [salida recortada]' : text;
    t.row.appendChild(pre);
  }

  _renderTodos(todos) {
    const wrap = document.createElement('div');
    wrap.className = 'tool-row-todos';
    const done = todos.filter(t => t.status === 'completed').length;
    const head = document.createElement('div');
    head.className = 'todos-head';
    head.textContent = `✓ Tareas (${done}/${todos.length})`;
    wrap.appendChild(head);
    todos.forEach(t => {
      const row = document.createElement('div');
      const st = t.status === 'completed' ? 'done' : t.status === 'in_progress' ? 'active' : 'pending';
      const icon = st === 'done' ? '✓' : st === 'active' ? '▶' : '○';
      row.className = 'todo-item ' + st;
      row.textContent = `${icon}  ${t.content}`;
      wrap.appendChild(row);
    });
    return wrap;
  }

  _renderDiff(result) {
    const wrap = document.createElement('div');
    wrap.className = 'tool-row-diff';
    const head = document.createElement('div');
    head.className = 'diff-head';
    const path = result.path ? String(result.path).replace(/\\/g, '/').split('/').pop() : 'archivo';
    let badge = '';
    if (result.syntax_ok === false) badge = ' <span class="diff-badge bad">⚠ sintaxis rota</span>';
    else if (result.syntax_ok === true) badge = ' <span class="diff-badge ok">✓ compila</span>';
    head.innerHTML = `✎ ${escHtml(path)} <span class="diff-stat">(${result.replacements || 1} cambio${(result.replacements || 1) === 1 ? '' : 's'})</span>${badge}`;
    wrap.appendChild(head);
    const pre = document.createElement('pre');
    pre.className = 'diff-body';
    result.diff.split('\n').forEach(line => {
      const span = document.createElement('span');
      const c = line[0];
      span.className = 'diff-line ' + (
        line.startsWith('+++') || line.startsWith('---') ? 'meta' :
        line.startsWith('@@') ? 'hunk' :
        c === '+' ? 'add' : c === '-' ? 'del' : 'ctx');
      span.textContent = line + '\n';
      pre.appendChild(span);
    });
    wrap.appendChild(pre);
    return wrap;
  }
  _setToolCancelled(id) {
    const t = this.toolRows.get(id);
    if (!t) return;
    t.status.textContent = 'cancelled';
    t.status.className   = 'tool-row-status cancelled';
    this._updateReportTool(id, 'cancelled');
  }

  // â”€â”€ Approval card â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  _showApproval(id, name, args, meta = {}) {
    this.pendingApproval = id;
    const dangerous = !!meta.dangerous;
    const alwaysAsk = isAlwaysAskTool(name, meta);
    const icon  = TOOL_ICONS[name] || 'tool';
    const color = dangerous ? 'approval-label-dangerous' : 'approval-label-safe';
    const cloudNote = alwaysAsk
      ? '<div class="approval-note">Consulta externa: esta acción siempre se aprueba por llamada y se redacta por defecto.</div>'
      : '';
    const alwaysBtn = alwaysAsk
      ? ''
      : '<button class="btn btn-always"  id="ap-always">Permitir siempre</button>';

    this.approvalOverlay.innerHTML = `
      <div class="approval-card ${dangerous ? 'dangerous' : ''}">
        <div class="approval-header">
          <span class="${color}">${icon}  ${escHtml(name)}</span>
          <span class="approval-warning">${escHtml(meta.category || 'tool')} · ${escHtml(meta.risk || 'low')}</span>
        </div>
        <div class="approval-guide">${escHtml(meta.guide || 'Revisa argumentos antes de ejecutar.')}</div>
        ${cloudNote}
        <pre class="approval-args">${escHtml(JSON.stringify(args, null, 2))}</pre>
        <div class="approval-btns">
          <button class="btn btn-execute" id="ap-exec">Ejecutar</button>
          ${alwaysBtn}
          <button class="btn btn-reject"  id="ap-reject">Rechazar</button>
        </div>
      </div>`;

    this.approvalOverlay.classList.add('visible');

    document.getElementById('ap-exec').onclick   = () => this._decide(id, name, true,  false);
    document.getElementById('ap-always')?.addEventListener('click', () => this._decide(id, name, true, true));
    document.getElementById('ap-reject').onclick = () => this._decide(id, name, false, false);
  }

  _decide(id, name, approved, always) {
    this.approvalOverlay.classList.remove('visible');
    this.approvalOverlay.innerHTML = '';
    this.pendingApproval = null;
    if (always && !isAlwaysAskTool(name)) {
      this.permissions[name] = 'auto';
      this._savePreferences();
      this._renderPermissionsList();
    }
    // Send directly — must NOT go into outbox (server timeout may have already expired)
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'approve', tool_id: id, approved }));
    }
    if (!approved) this._setToolCancelled(id);
  }

  _hideApproval() {
    this.approvalOverlay.classList.remove('visible');
    this.approvalOverlay.innerHTML = '';
    this.pendingApproval = null;
  }

  // â”€â”€ Camera / Images â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  openCamera() {
    const input = document.createElement('input');
    input.type   = 'file';
    input.accept = 'image/*';
    input.multiple = true;
    input.onchange = e => this._attachFiles(e.target.files);
    input.click();
  }

  async captureScreen() {
    let stream;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      const track  = stream.getVideoTracks()[0];
      const cap    = new ImageCapture(track);
      const bitmap = await cap.grabFrame();
      const canvas = document.createElement('canvas');
      canvas.width  = bitmap.width;
      canvas.height = bitmap.height;
      canvas.getContext('2d').drawImage(bitmap, 0, 0);
      const dataUrl = canvas.toDataURL('image/jpeg', 0.75);
      this._attachImage(dataUrl);
    } catch (e) {
      if (e.name !== 'NotAllowedError') {
        console.warn('Screen capture:', e);
      }
    } finally {
      if (stream) stream.getTracks().forEach(t => t.stop());
    }
  }

  _attachImage(dataUrl) {
    if (this.attachedImgs.length >= 4) {
      this._setStatus('error', 'maximo 4 imagenes');
      return;
    }
    const b64 = dataUrl.includes(',') ? dataUrl.split(',')[1] : dataUrl;
    this.attachedImgs.push({ dataUrl, b64 });

    const thumb = document.createElement('div');
    thumb.className = 'attachment-thumb';
    const img = document.createElement('img');
    img.src = dataUrl;
    const rm = document.createElement('button');
    rm.className = 'attachment-remove';
    rm.textContent = 'x';
    rm.onclick = () => {
      const idx = this.attachedImgs.findIndex(i => i.dataUrl === dataUrl);
      if (idx > -1) this.attachedImgs.splice(idx, 1);
      thumb.remove();
    };
    thumb.appendChild(img);
    thumb.appendChild(rm);
    this.attachEl.appendChild(thumb);
  }

  _attachFiles(files) {
    Array.from(files || [])
      .filter(file => file.type?.startsWith('image/'))
      .slice(0, Math.max(0, 4 - this.attachedImgs.length))
      .forEach(file => {
        const reader = new FileReader();
        reader.onload = ev => this._attachImage(ev.target.result);
        reader.readAsDataURL(file);
      });
  }

  _resetAttachments() {
    this.attachedImgs = [];
    this.attachEl.innerHTML = '';
  }

  // â”€â”€ Voice â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  toggleVoice() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('Reconocimiento de voz no disponible en este navegador'); return; }

    if (this._recog) {
      this._recog.stop();
      this._recog = null;
      this.$('voice-btn').classList.remove('active');
      return;
    }

    const recog = new SR();
    recog.lang = navigator.language || 'es-ES';
    recog.continuous = false;
    recog.interimResults = true;

    recog.onresult = e => {
      const t = Array.from(e.results).map(r => r[0].transcript).join('');
      this.inputEl.value = t;
      this._autoResize();
    };
    recog.onend = () => {
      this.$('voice-btn').classList.remove('active');
      this._recog = null;
    };
    recog.onerror = () => {
      this.$('voice-btn').classList.remove('active');
      this._recog = null;
    };

    recog.start();
    this._recog = recog;
    this.$('voice-btn').classList.add('active');
  }

  // â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  _beginStreaming() {
    this.streaming = true;
    this.toolRows.clear();
    this.currentBubble = null;
    this.sendBtn.style.display = 'none';
    this.stopBtn.style.display = '';
    this._setInputLocked(true);
    this._setStatus('thinking', 'generando...');
  }

  _endStreaming() {
    this.streaming = false;
    this.sendBtn.style.display = '';
    this.stopBtn.style.display = 'none';
    if (this.ws?.readyState === WebSocket.OPEN && this.pcOnline) {
      this._setInputLocked(false);
      this.inputEl.focus();
      this._setConnectionState('', 'conectado');
    }
    this._hideApproval();
  }

  _setStatus(cls, text) {
    this.statusDot.className = `status-dot ${cls}`;
    document.getElementById('status-text').textContent = text;
    this.report.status.push({ ts: new Date().toISOString(), cls, text });
  }

  _setConnectionState(cls, text, bannerText = '', lockInput = false) {
    if (this.reconnectNoticeTimer) {
      clearTimeout(this.reconnectNoticeTimer);
      this.reconnectNoticeTimer = null;
    }
    this._setStatus(cls, text);
    this._setInputLocked(lockInput || this.streaming);
    if (bannerText) {
      this._showConnectionBanner(cls, bannerText);
    } else {
      this._hideConnectionBanner();
    }
  }

  _handleDisconnect(text) {
    this.pcOnline = true;
    this._setStatus('offline', text);
    this._setInputLocked(true);
    if (this.reconnectNoticeTimer) clearTimeout(this.reconnectNoticeTimer);
    this.reconnectNoticeTimer = setTimeout(() => {
      this._showConnectionBanner('offline', 'Reconectando con el relay. El envio se reactivara automaticamente.');
    }, 3000);
  }

  _clearTransientConversationState() {
    this.toolRows.clear();
    this.currentBubble = null;
    this._hideApproval();
  }

  _setInputLocked(locked) {
    this.inputEl.disabled = locked;
    this.sendBtn.disabled = locked;
  }

  _ensureConnectionBanner() {
    this.connectionBanner = document.getElementById('connection-banner');
    if (this.connectionBanner) return;
    this.connectionBanner = document.createElement('div');
    this.connectionBanner.id = 'connection-banner';
    this.connectionBanner.setAttribute('role', 'status');
    this.connectionBanner.setAttribute('aria-live', 'polite');
    const header = document.querySelector('header');
    header.insertAdjacentElement('afterend', this.connectionBanner);
  }

  _showConnectionBanner(cls, text) {
    this._ensureConnectionBanner();
    this.connectionBanner.className = `visible ${cls || 'offline'}`;
    this.connectionBanner.textContent = text;
  }

  _hideConnectionBanner() {
    this._ensureConnectionBanner();
    this.connectionBanner.className = '';
    this.connectionBanner.textContent = '';
  }

  _prefsKey() {
    return `ca_prefs_${location.host}`;
  }

  _loadPreferences() {
    try {
      const prefs = JSON.parse(localStorage.getItem(this._prefsKey()) || '{}');
      // Por defecto: modo mixto (Mistral Medium 3 + local). Si el usuario eligió
      // Auto explícitamente (''), se respeta con ?? (solo cae a fused si no hay pref).
      this.selectedModel = prefs.selectedModel ?? '';   // por defecto: LOCAL (gratis)
      this.sessionTrust = !!prefs.sessionTrust;
      this.permissions = prefs.permissions && typeof prefs.permissions === 'object' ? prefs.permissions : {};
    } catch {
      this.selectedModel = '';
      this.sessionTrust = false;
      this.permissions = {};
    }
  }

  _savePreferences() {
    localStorage.setItem(this._prefsKey(), JSON.stringify({
      selectedModel: this.selectedModel,
      sessionTrust: this.sessionTrust,
      permissions: this.permissions,
    }));
  }

  _initSettingsPanel() {
    this.settingsPanel = document.getElementById('settings-panel');
    this.settingsBackdrop = document.getElementById('settings-backdrop');
    const settingsBtn = document.getElementById('settings-btn');
    if (!this.settingsPanel || !settingsBtn) return;

    settingsBtn.addEventListener('click', () => this._toggleSettingsPanel());
    this.settingsBackdrop?.addEventListener('click', () => this._toggleSettingsPanel(false));
    this.$('settings-close')?.addEventListener('click', () => this._toggleSettingsPanel(false));
    this.$('model-select')?.addEventListener('change', e => {
      this.selectedModel = e.target.value;
      this._savePreferences();
    });
    this.$('trust-toggle')?.addEventListener('change', e => {
      this.sessionTrust = e.target.checked;
      this._savePreferences();
    });
    this.$('permissions-list')?.addEventListener('change', e => {
      if (e.target?.dataset?.tool) {
        this.permissions[e.target.dataset.tool] = e.target.value;
        this._savePreferences();
      }
    });
    this._syncSettingsPanel();
  }

  _toggleSettingsPanel(force) {
    if (!this.settingsPanel) return;
    const open = force ?? !this.settingsPanel.classList.contains('open');
    this.settingsPanel.classList.toggle('open', open);
    this.settingsBackdrop?.classList.toggle('open', open);
  }

  _syncSettingsPanel() {
    const trust = this.$('trust-toggle');
    if (trust) trust.checked = this.sessionTrust;
    this._syncModelSelect();
    this._renderPermissionsList();
  }

  _syncModelSelect() {
    const select = this.$('model-select');
    if (!select) return;
    const LABELS = {
      '': '🔀 Auto (decide solo)',
      'auto': '🔀 Auto (decide solo)',
      'fused': '🤝 Fusionado (Mistral + local)',
      'codestral-latest': '💻 Codestral (código)',
      'mistral-large-latest': '🧠 Mistral Large',
      'mistral-medium-latest': '🧠 Mistral Medium',
    };
    const prettyLocal = (m) => '🖥️ ' + m.replace(/:latest$/, '');
    // Opciones SIEMPRE disponibles: el modo fusionado y los modelos de nube NO
    // aparecen en availableModels (que solo lista los Ollama locales del host),
    // así que los añadimos a mano o el selector se queda casi vacío.
    const VIRTUAL = [
      { value: 'fused',                 label: '🤝 Fusionado (Mistral Small + local)' },
      { value: 'codestral-latest',      label: '💻 Codestral (código, barato)' },
      { value: 'mistral-small-latest',  label: '⚡ Mistral Small (barato)' },
      { value: 'mistral-medium-latest', label: '🧠 Mistral Medium (caro)' },
      { value: 'mistral-large-latest',  label: '🧠 Mistral Large (muy caro)' },
    ];
    const virtualValues = new Set(VIRTUAL.map(v => v.value));
    const known = [
      { value: '', label: LABELS[''] },
      ...VIRTUAL,
      ...this.availableModels
        .filter(model => model !== 'auto' && !virtualValues.has(model))   // '' ya representa Auto
        .map(model => ({
          value: model,
          label: LABELS[model] || (/mistral|magistral|pixtral/i.test(model) ? '🧠 ' + model : prettyLocal(model)),
        })),
    ];
    const seen = new Set();
    select.innerHTML = '';
    known.forEach(opt => {
      if (seen.has(opt.value)) return;
      seen.add(opt.value);
      const el = document.createElement('option');
      el.value = opt.value;
      el.textContent = opt.label;
      select.appendChild(el);
    });
    const normalizedModel = this.selectedModel === 'auto' ? '' : this.selectedModel;
    if (seen.has(normalizedModel)) {
      select.value = normalizedModel;
      if (this.selectedModel !== normalizedModel) {
        this.selectedModel = normalizedModel;
        this._savePreferences();
      }
    } else {
      select.value = '';
      if (this.selectedModel) {
        this.selectedModel = '';
        this._savePreferences();
      }
    }
  }

  _renderPermissionsList() {
    const list = this.$('permissions-list');
    if (!list) return;
    const toolNames = Array.from(new Set([
      ...Object.keys(TOOL_ICONS),
      ...Object.keys(this.permissions),
    ])).sort();
    list.innerHTML = toolNames.map(name => {
      const locked = isAlwaysAskTool(name);
      const note = locked ? '<small>cloud: preguntar siempre</small>' : '';
      const auto = locked ? '' : '<option value="auto">Auto</option>';
      return `
      <label class="permission-row">
        <span>${escHtml(name)}${note}</span>
        <select data-tool="${escHtml(name)}">
          <option value="ask">Preguntar</option>
          ${auto}
          <option value="block">Bloquear</option>
        </select>
      </label>`;
    }).join('');
    list.querySelectorAll('select[data-tool]').forEach(sel => {
      const name = sel.dataset.tool;
      const value = this.permissions[name] || 'ask';
      sel.value = isAlwaysAskTool(name) && value === 'auto' ? 'ask' : value;
    });
  }

  _installReportButton() {
    if (document.getElementById('report-btn')) return;
    const btn = document.createElement('button');
    btn.id = 'report-btn';
    btn.textContent = 'Reporte';
    btn.title = 'Descargar reporte de sesion';
    btn.addEventListener('click', () => this.downloadReport('json'));
    const headerStatus = document.querySelector('.header-status');
    if (!headerStatus) return;
    const logout = document.getElementById('logout-btn');
    headerStatus.insertBefore(btn, logout || null);
  }

  _recordReportEvent(type, data) {
    if (type === 'status') return;
    if (type === 'error') {
      this.report.errors.push({ ts: new Date().toISOString(), message: redactReportValue(String(data)) });
    }
  }

  _updateReportTool(id, status, result = null) {
    const row = this.report.tools.find(t => t.id === id);
    if (!row) return;
    row.status = status;
    row.finishedAt = new Date().toISOString();
    if (result !== null) row.resultPreview = this._preview(redactReportValue(result), 1200);
  }

  _preview(value, max) {
    const text = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    return text.length > max ? text.slice(0, max) + '\n... [recortado]' : text;
  }

  downloadReport(format = 'json') {
    const report = {
      ...this.report,
      generatedAt: new Date().toISOString(),
      endedAt: new Date().toISOString(),
      device: `${this.isMobile ? 'movil' : 'PC'} ${this.platform}`,
      url: location.href,
      userAgent: navigator.userAgent,
    };
    const isHtml = format === 'html';
    const safeReport = redactReportValue(report);
    const body = isHtml ? this._reportHtml(safeReport) : JSON.stringify(safeReport, null, 2);
    const blob = new Blob([body], { type: isHtml ? 'text/html' : 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `cyberagent-session-${new Date().toISOString().replace(/[:.]/g, '-')}.${isHtml ? 'html' : 'json'}`;
    a.style.display = 'none';
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      URL.revokeObjectURL(a.href);
      a.remove();
    }, 1000);
  }

  _reportHtml(report) {
    return `<!doctype html><meta charset="utf-8"><title>CyberAgent report</title>
<style>body{font-family:system-ui;background:#0b0d10;color:#edf2f7;padding:24px;line-height:1.5}pre{white-space:pre-wrap;background:#15191f;border:1px solid #303946;border-radius:8px;padding:16px}</style>
<h1>CyberAgent session report</h1><pre>${escHtml(JSON.stringify(report, null, 2))}</pre>`;
  }

  _scrollBottom() {
    // Auto-scroll "pegajoso": solo seguimos al fondo si el usuario ya estaba
    // cerca del fondo. Si subió a leer, no le arrancamos la vista.
    if (this._stick === undefined) {
      this._stick = true;
      this.messages.addEventListener('scroll', () => {
        const m = this.messages;
        this._stick = (m.scrollHeight - m.scrollTop - m.clientHeight) < 90;
      }, { passive: true });
    }
    if (!this._stick) return;
    requestAnimationFrame(() => {
      this.messages.scrollTop = this.messages.scrollHeight;
    });
  }

  _removeWelcome() {
    const w = this.messages.querySelector('.welcome');
    if (w) w.remove();
  }

  _showWelcome() {
    if (this.messages.querySelector('.msg')) return;
    this.messages.innerHTML = `
      <div class="welcome">
        <div class="welcome-icon">CA</div>
        <h2>CyberAgent</h2>
        <p>Agente de IA con acceso completo al sistema. Tu inferencia, tu hardware.</p>
        <div class="welcome-suggestions">
          <button class="suggestion" onclick="app.suggest(this)">Que procesos estan usando mas CPU?</button>
          <button class="suggestion" onclick="app.suggest(this)">Escanea los puertos abiertos en esta red</button>
          <button class="suggestion" onclick="app.suggest(this)">Instala y configura nmap</button>
        </div>
      </div>`;
  }

  suggest(btn) {
    this.inputEl.value = btn.textContent;
    this._autoResize();
    this.inputEl.focus();
  }

  _autoResize() {
    this.inputEl.style.height = 'auto';
    this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 140) + 'px';
  }

  // â”€â”€ Event bindings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  _bindUI() {
    this.sendBtn.addEventListener('click', () => this.send());
    this.stopBtn.addEventListener('click', () => this.stop());

    this.inputEl.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); this.send(); }
    });
    this.inputEl.addEventListener('input', () => this._autoResize());

    // Paste image
    document.addEventListener('paste', e => {
      const items = e.clipboardData?.items || [];
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          const reader = new FileReader();
          reader.onload = ev => this._attachImage(ev.target.result);
          reader.readAsDataURL(item.getAsFile());
        }
      }
    });

    this.$('camera-btn').addEventListener('click', () => this.openCamera());
    this.$('screen-btn').addEventListener('click', () => this.captureScreen());
    this.$('voice-btn').addEventListener('click',  () => this.toggleVoice());
  }

  _bindDragDrop() {
    const area = document.getElementById('input-area');
    if (!area) return;
    ['dragenter', 'dragover'].forEach(type => {
      area.addEventListener(type, e => {
        e.preventDefault();
        area.classList.add('drag-over');
      });
    });
    ['dragleave', 'drop'].forEach(type => {
      area.addEventListener(type, e => {
        e.preventDefault();
        area.classList.remove('drag-over');
      });
    });
    area.addEventListener('drop', e => {
      this._attachFiles(e.dataTransfer?.files || []);
    });
  }
}

// â”€â”€ Boot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const app = new CyberAgent();
window.app = app;
