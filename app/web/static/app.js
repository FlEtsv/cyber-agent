'use strict';

const TOOL_ICONS = {
  shell:'>', run_python:'py', write_file:'edit', read_file:'file',
  list_directory:'dir', web_fetch:'web', list_processes:'proc',
  screenshot:'screen', screenshot_pc:'screen', install_package:'install',
  uninstall_package:'remove', system_info:'info',
};

const CATEGORY_ICONS = {
  core:'core', web:'web', files:'file', system:'sys', desktop:'desk',
  network:'net', forensics:'lab', encode:'enc', rag:'rag',
  self:'self', mobile:'mob', other:'tool',
};

// â”€â”€ Markdown renderer (via marked CDN) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
function renderMd(text) {
  if (!text) return '';
  try {
    return marked.parse(text, { breaks: true, gfm: true });
  } catch {
    return escHtml(text);
  }
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
    this.outbox        = [];
    this.reconnectDelay = 1500;
    this.reconnectTimer = null;
    this.reconnectNoticeTimer = null;
    this.connectionBanner = null;
    this.pcOnline = true;
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

    this._ensureConnectionBanner();
    this._installReportButton();
    this._bindUI();
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
    this.ws.onerror = () => this._setConnectionState('error', 'error WS', 'Error de conexion con el agente.', true);
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
  // â”€â”€ Incoming events â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  _onMessage(evt) {
    const { type, data } = evt;
    this._recordReportEvent(type, data);

    switch (type) {
      case 'connected':
        this.pcOnline = data?.pc_online !== false;
        if (!this.pcOnline) {
          this._setConnectionState('offline', 'PC offline', 'El PC principal no esta conectado al relay.', true);
        } else {
          this._setConnectionState('', 'conectado');
        }
        if (data?.models?.length) {
          document.querySelector('.header-model').textContent =
            data.models.find(m => m === 'cyberagent-original') ||
            data.models.find(m => m.includes('cyber')) ||
            data.models[0] ||
            '';
        }
        this._showWelcome();
        break;

      case 'status':
        this._setStatus('thinking', data);
        break;

      case 'token':
        this._ensureAIBubble();
        this.currentBubble._raw += data;
        this._renderCurrentBubble();
        this._scrollBottom();
        break;

      case 'tool_call':
        this._ensureAIBubble();
        this._addToolActivity(data.id, data.name, data.args, data);
        break;

      case 'need_approval':
        this._showApproval(data.id, data.name, data.args, data);
        break;

      case 'tool_result':
        this._setToolDone(data.id, data.result ?? data.output ?? data.content ?? data);
        break;

      case 'vision_processing':
        this._setStatus('thinking', data);
        break;

      case 'done':
        this._finalizeAIBubble();
        this._endStreaming();
        break;

      case 'error':
        if (typeof data === 'string' && /pc no conectado|pc no est/i.test(data)) {
          this.pcOnline = false;
          this._setConnectionState('offline', 'PC offline', data, true);
        }
        this._addErrorMsg(data);
        this._endStreaming();
        break;
    }
  }

  // â”€â”€ Send message â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  send() {
    const text = this.inputEl.value.trim();
    if ((!text && this.attachedImgs.length === 0) || this.streaming) return;
    if (this.ws?.readyState !== WebSocket.OPEN || !this.pcOnline) {
      this._setConnectionState('offline', this.pcOnline ? 'reconectando...' : 'PC offline',
        this.pcOnline ? 'Esperando reconexion con CyberAgent.' : 'El PC principal no esta conectado al relay.', true);
      return;
    }

    this._beginStreaming();
    this._addUserBubble(text, this.attachedImgs.map(i => i.dataUrl));

    this._send({
      type:          'message',
      content:       text,
      images:        this.attachedImgs.map(i => i.b64),
      session_trust: this.sessionTrust,
      permissions:   this.permissions,
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

  _addUserBubble(text, imageSrcs = []) {
    this.report.messages.push({
      ts: new Date().toISOString(),
      role: 'user',
      text: redactReportValue(text),
      images: imageSrcs.length,
    });
    const wrap = document.createElement('div');
    wrap.className = 'msg user';

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
      content.textContent = text;
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

    const contentEl = document.createElement('div');
    contentEl.className = 'msg-content';
    body.appendChild(contentEl);

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

    wrap.appendChild(avatar);
    wrap.appendChild(body);
    this.messages.appendChild(wrap);

    this.currentBubble = {
      el: wrap,
      contentEl,
      actionsSection,
      actionsList,
      toggle,
      _raw: '',
      _count: 0,
    };

    this._scrollBottom();
  }

  _renderCurrentBubble() {
    if (!this.currentBubble) return;
    this.currentBubble.contentEl.innerHTML = renderMd(this.currentBubble._raw);
  }

  _finalizeAIBubble() {
    if (!this.currentBubble) return;
    this._renderCurrentBubble();
    this.report.messages.push({
      ts: new Date().toISOString(),
      role: 'assistant',
      text: redactReportValue(this.currentBubble._raw),
    });
    this.currentBubble = null;
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
    if (result !== null && !t.row.querySelector('.tool-row-result')) {
      const pre = document.createElement('pre');
      pre.className = 'tool-row-result';
      const text = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
      pre.textContent = text.length > 3000 ? text.slice(0, 3000) + '\n... [salida recortada]' : text;
      t.row.appendChild(pre);
    }
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
    const icon  = TOOL_ICONS[name] || 'tool';
    const color = dangerous ? 'approval-label-dangerous' : 'approval-label-safe';

    this.approvalOverlay.innerHTML = `
      <div class="approval-card ${dangerous ? 'dangerous' : ''}">
        <div class="approval-header">
          <span class="${color}">${icon}  ${escHtml(name)}</span>
          <span class="approval-warning">${escHtml(meta.category || 'tool')} · ${escHtml(meta.risk || 'low')}</span>
        </div>
        <div class="approval-guide">${escHtml(meta.guide || 'Revisa argumentos antes de ejecutar.')}</div>
        <pre class="approval-args">${escHtml(JSON.stringify(args, null, 2))}</pre>
        <div class="approval-btns">
          <button class="btn btn-execute" id="ap-exec">Ejecutar</button>
          <button class="btn btn-always"  id="ap-always">Permitir siempre</button>
          <button class="btn btn-reject"  id="ap-reject">Rechazar</button>
        </div>
      </div>`;

    this.approvalOverlay.classList.add('visible');

    document.getElementById('ap-exec').onclick   = () => this._decide(id, name, true,  false);
    document.getElementById('ap-always').onclick = () => this._decide(id, name, true,  true);
    document.getElementById('ap-reject').onclick = () => this._decide(id, name, false, false);
  }

  _decide(id, name, approved, always) {
    this.approvalOverlay.classList.remove('visible');
    this.approvalOverlay.innerHTML = '';
    this.pendingApproval = null;
    if (always) this.permissions[name] = 'auto';
    // Send approval directly — must NOT go into outbox (server timeout may have already expired)
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
    input.onchange = e => {
      Array.from(e.target.files).slice(0, 4).forEach(file => {
        const reader = new FileReader();
        reader.onload = ev => this._attachImage(ev.target.result);
        reader.readAsDataURL(file);
      });
    };
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
      this._showConnectionBanner('offline', 'Reconectando con CyberAgent. El envio se reactivara automaticamente.');
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
}

// â”€â”€ Boot â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
const app = new CyberAgent();
