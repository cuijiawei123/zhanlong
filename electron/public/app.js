// app.js — 斩龙 Electron 前端（Obsidian Monolith 设计系统）

let macros = [];
let isListening = false;
let editingName = null;
let isRecording = false;
let triggerCount = 0;
let logIndex = 0;
let sessionStart = null;
let uptimeTimer = null;

// ═══════════ 初始化 ═══════════

async function init() {
  showPage('home');

  // 首次启动显示欢迎页
  if (!localStorage.getItem('zhanlong_welcomed')) {
    showWelcome();
  }

  try {
    await window.api.connect();
    updateConnectionStatus(true);

    window.api.onTrigger(({ name }) => {
      triggerCount++;
      const tp = document.getElementById('log-triggers-page');
      if (tp) tp.textContent = triggerCount.toLocaleString();
      addLogEntry('trigger', `${t('log_trigger')}: <span class="bg-secondary/10 px-1.5 py-0.5 rounded border border-secondary/20 font-bold">${esc(name)}</span>`);
    });

    window.api.onStatus(({ status }) => handleStatus(status));
    window.api.onLog(({ message }) => addLogEntry('info', message));

    await loadMacros();
  } catch (e) {
    console.error('Init failed, retrying...', e);
    updateConnectionStatus(false);
    setTimeout(init, 1500);
  }
}

function updateConnectionStatus(online) {
  const dot = document.getElementById('status-dot');
  const label = document.getElementById('status-label');
  const fDot = document.getElementById('footer-dot');
  const fLabel = document.getElementById('footer-status');
  if (online) {
    dot.className = 'w-2 h-2 rounded-full bg-primary shadow-[0_0_6px_rgba(158,202,255,0.5)]';
    label.textContent = 'Online'; label.className = 'text-[10px] font-bold tracking-widest uppercase text-primary';
    fDot.className = 'w-1.5 h-1.5 rounded-full bg-primary shadow-[0_0_5px_rgba(158,202,255,0.5)]';
    fLabel.textContent = 'Voice Engine Online'; fLabel.className = 'text-[9px] font-bold text-on-surface uppercase tracking-widest';
  } else {
    dot.className = 'w-2 h-2 rounded-full bg-outline';
    label.textContent = 'Offline'; label.className = 'text-[10px] font-bold tracking-widest uppercase text-outline';
    fDot.className = 'w-1.5 h-1.5 rounded-full bg-outline';
    fLabel.textContent = 'Engine Offline'; fLabel.className = 'text-[9px] font-bold text-outline uppercase tracking-widest';
  }
}

// ═══════════ 导航 ═══════════

function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(a => {
    if (a.dataset.page === name) {
      a.className = 'nav-item flex items-center gap-3 px-4 py-2.5 rounded-sm cursor-pointer transition-all bg-surface-container-high text-primary border-r-2 border-secondary';
    } else {
      a.className = 'nav-item flex items-center gap-3 px-4 py-2.5 rounded-sm cursor-pointer transition-all text-on-surface-variant hover:bg-surface-container-low';
    }
  });
}

// ═══════════ 宏数据 ═══════════

async function loadMacros() {
  try {
    const result = await window.api.getConfig();
    macros = result.items || [];
    renderMacroGrid();
    // 更新首页宏计数
    const countEl = document.getElementById('home-macro-count');
    if (countEl) countEl.textContent = macros.length;
  } catch (e) { console.error('Load failed:', e); }
}

function renderMacroGrid() {
  const grid = document.getElementById('macro-grid');
  let html = '';

  if (macros.length === 0) {
    html = `<div class="col-span-2 text-center py-16 text-on-surface-variant opacity-60">${t('macros_empty')}</div>`;
  }

  macros.forEach((m, i) => {
    const keysHtml = renderKeysHtml(m.keys || '');
    html += `
    <div class="group relative bg-surface-container-low p-6 rounded-xl hover:bg-surface-container-high border border-outline-variant/5 transition-all duration-300">
      <div class="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1.5">
        <button onclick="openEdit('${esc(m.name)}')" class="p-1.5 hover:bg-surface-container-highest rounded text-on-surface-variant transition-colors">
          <span class="material-symbols-outlined text-base">edit</span>
        </button>
        <button onclick="deleteMacro('${esc(m.name)}')" class="p-1.5 hover:bg-secondary-container/20 rounded text-secondary transition-colors">
          <span class="material-symbols-outlined text-base">delete</span>
        </button>
      </div>
      <div class="mb-6">
        <h2 class="text-3xl font-headline font-bold text-on-surface">${esc(m.name)}</h2>
        <p class="text-primary font-mono text-sm tracking-[0.15em] mt-1 opacity-80">${m.voice ? esc(m.voice) : `<span class="text-outline-variant italic">${t('no_voice')}</span>`}</p>
      </div>
      <div class="flex items-center gap-2 flex-wrap">${keysHtml || `<span class="text-outline-variant text-xs italic">${t('no_keys')}</span>`}</div>
    </div>`;
  });

  html += `
  <button onclick="openAdd()" class="group border-2 border-dashed border-outline-variant/20 rounded-xl hover:border-primary/40 hover:bg-primary/5 transition-all duration-300 flex flex-col items-center justify-center gap-2 min-h-[160px]">
    <span class="material-symbols-outlined text-3xl text-outline-variant group-hover:text-primary transition-colors">add_circle</span>
    <span class="font-headline font-bold text-xs tracking-widest text-on-surface-variant group-hover:text-primary uppercase transition-colors">${t('add_macro')}</span>
  </button>`;

  grid.innerHTML = html;
}

function renderKeysHtml(keysStr) {
  if (!keysStr) return `<span class="text-outline-variant text-xs italic">${t('no_keys')}</span>`;
  // 组合键 (ctrl, c) → 分拆为标签
  const parts = keysStr.split(/\s+/);
  return parts.map(p => {
    if (p.startsWith('(') && p.endsWith(')')) {
      const inner = p.slice(1, -1).split(',').map(k => k.trim());
      return inner.map(k => `<span class="bg-primary-container px-2 py-0.5 rounded text-[11px] font-bold text-on-primary-container font-headline uppercase">${esc(k)}</span>`).join('<span class="text-on-surface-variant text-xs mx-0.5">+</span>');
    }
    return `<span class="bg-surface-container-lowest px-2.5 py-0.5 rounded text-[11px] font-bold text-primary font-headline uppercase border border-outline-variant/10 flex items-center gap-1.5"><span class="material-symbols-outlined text-[10px] text-on-surface-variant">keyboard</span>${esc(p)}</span>`;
  }).join(' ');
}

// ═══════════ 监听 ═══════════

async function toggleListen() {
  const btn = document.getElementById('btn-listen');
  if (isListening) {
    await window.api.stopListening();
  } else {
    btn.querySelector('#listen-text').textContent = t('listen_starting');
    btn.disabled = true;
    await window.api.startListening();
  }
}

function handleStatus(status) {
  const btn = document.getElementById('btn-listen');
  const badge = document.getElementById('system-badge');
  if (status === 'listening') {
    isListening = true;
    btn.disabled = false;
    btn.querySelector('#listen-text').textContent = t('listen_stop');
    btn.className = 'bg-secondary-container text-on-secondary-container px-3 py-1 rounded text-[11px] flex items-center gap-2 hover:opacity-90 transition-all active:scale-95 font-bold tracking-tight no-drag';
    badge.innerHTML = `<span class="w-2.5 h-2.5 rounded-full bg-secondary animate-pulse shadow-[0_0_10px_rgba(255,180,172,0.5)]"></span><span class="text-[10px] font-bold tracking-widest uppercase text-secondary">${t('system_listening')}</span>`;
    sessionStart = Date.now(); triggerCount = 0;
    startUptimeTimer();
    addLogEntry('start', t('log_started'));
    showPage('logs');
  } else if (status === 'stopped') {
    isListening = false;
    btn.disabled = false;
    btn.querySelector('#listen-text').textContent = t('listen_start');
    btn.className = 'bg-primary-container text-on-primary-container px-3 py-1 rounded text-[11px] flex items-center gap-2 hover:bg-surface-container-highest transition-colors active:scale-95 font-bold tracking-tight no-drag';
    badge.innerHTML = `<span class="w-2 h-2 rounded-full bg-outline"></span><span class="text-[10px] font-bold tracking-widest uppercase text-on-surface-variant">${t('system_ready')}</span>`;
    stopUptimeTimer();
    addLogEntry('stop', t('log_stopped'));
  } else if (status.startsWith('error')) {
    isListening = false; btn.disabled = false;
    btn.querySelector('#listen-text').textContent = t('listen_start');
    addLogEntry('error', status);
  }
}

// ═══════════ 日志 ═══════════

function addLogEntry(type, html) {
  logIndex++;
  const colors = { start:'text-primary', stop:'text-error', trigger:'text-secondary', error:'text-error', info:'text-on-surface-variant' };
  const icons = { start:'check_circle', stop:'cancel', trigger:'target', error:'error', info:'info' };
  const now = new Date().toLocaleString('zh-CN', { hour12:false, year:'numeric', month:'2-digit', day:'2-digit', hour:'2-digit', minute:'2-digit', second:'2-digit' });

  const entryHtml = `
    <div class="flex items-start gap-4 group py-0.5 hover:bg-${type === 'trigger' ? 'secondary' : 'primary'}/5 rounded px-2 -mx-2 transition-colors">
      <span class="text-on-surface-variant/30 shrink-0 select-none w-6 text-right text-xs">${String(logIndex).padStart(2,'0')}</span>
      <div class="flex items-center gap-3 ${colors[type] || 'text-on-surface-variant'}">
        <span class="material-symbols-outlined text-[10px]" style="font-variation-settings:'FILL' 1">${icons[type] || 'info'}</span>
        <span class="opacity-50 text-[11px] w-36 shrink-0">${now}</span>
        <span class="text-on-surface">— ${html}</span>
      </div>
    </div>`;

  // 写入日志页面
  const pageStream = document.getElementById('log-stream-page');
  if (pageStream) {
    const w = pageStream.querySelector('.animate-pulse');
    if (w) w.parentElement.remove();
    pageStream.insertAdjacentHTML('beforeend', entryHtml);
    pageStream.scrollTop = pageStream.scrollHeight;
  }

  // 同步 triggers 计数到日志页面
  const tp = document.getElementById('log-triggers-page');
  if (tp) tp.textContent = triggerCount.toLocaleString();
}

function clearLog() {
  const waitingHtml = '<div class="flex items-center gap-2 py-0.5 px-2"><span class="w-1.5 h-3 bg-primary/60 animate-pulse"></span><span class="text-[10px] text-primary/40 uppercase font-bold tracking-tighter">' + t('log_waiting') + '</span></div>';
  const page = document.getElementById('log-stream-page');
  if (page) page.innerHTML = waitingHtml;
  logIndex = 0;
}

function startUptimeTimer() {
  stopUptimeTimer();
  uptimeTimer = setInterval(() => {
    if (!sessionStart) return;
    const d = Math.floor((Date.now() - sessionStart) / 1000);
    const h = String(Math.floor(d/3600)).padStart(2,'0');
    const m = String(Math.floor((d%3600)/60)).padStart(2,'0');
    const s = String(d%60).padStart(2,'0');
    document.getElementById('log-uptime-page').textContent = `${h}:${m}:${s}`;
  }, 1000);
}
function stopUptimeTimer() { if (uptimeTimer) { clearInterval(uptimeTimer); uptimeTimer = null; } }

// ═══════════ 编辑弹窗 ═══════════

function openAdd() {
  editingName = null;
  document.getElementById('edit-title').textContent = t('edit_new_title');
  document.getElementById('edit-name').value = ''; document.getElementById('edit-name').readOnly = false;
  document.getElementById('edit-keys').value = '';
  document.getElementById('edit-voice').value = '';
  document.getElementById('edit-overlay').classList.add('active');
}

function openEdit(name) {
  editingName = name;
  const item = macros.find(m => m.name === name);
  if (!item) return;
  document.getElementById('edit-title').textContent = `${t('edit_title_prefix')} ${name}`;
  document.getElementById('edit-name').value = name; document.getElementById('edit-name').readOnly = true;
  document.getElementById('edit-keys').value = item.keys || '';
  document.getElementById('edit-voice').value = item.voice || '';
  document.getElementById('edit-overlay').classList.add('active');
}

function closeEdit() { document.getElementById('edit-overlay').classList.remove('active'); }

async function saveEdit() {
  const name = document.getElementById('edit-name').value.trim();
  const keys = document.getElementById('edit-keys').value.trim();
  const voice = document.getElementById('edit-voice').value.trim();
  if (!name) { alert(t('alert_no_name')); return; }
  if (!keys) { alert(t('alert_no_keys')); return; }
  try {
    await window.api.saveMacro(name, keys, voice);
    closeEdit();
    await loadMacros();
  } catch (e) { alert(t('alert_save_fail') + ': ' + e.message); }
}

async function deleteMacro(name) {
  if (!confirm(t('confirm_delete', { name }))) return;
  try { await window.api.deleteMacro(name); await loadMacros(); }
  catch (e) { alert(t('alert_delete_fail') + ': ' + e.message); }
}

// ═══════════ 话筒 ═══════════

async function micDown() {
  if (isRecording) return;
  try { await window.api.startRecording(); isRecording = true;
    document.getElementById('edit-voice').value = t('mic_recording');
    document.getElementById('edit-mic').classList.add('!bg-secondary-container');
  } catch(e) {}
}
async function micUp() {
  if (!isRecording) return;
  document.getElementById('edit-mic').classList.remove('!bg-secondary-container');
  document.getElementById('edit-voice').value = t('mic_recognizing');
  try {
    const r = await window.api.stopRecording(); isRecording = false;
    document.getElementById('edit-voice').value = r.text === '错误' ? '' : (r.pinyin || '');
  } catch(e) { isRecording = false; document.getElementById('edit-voice').value = ''; }
}

// ═══════════ 工具 ═══════════

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

// ═══════════ 启动 ═══════════

window.addEventListener('DOMContentLoaded', init);

// ESC 关闭编辑弹窗
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeEdit(); });

// 点击 overlay 背景关闭
document.getElementById('edit-overlay')?.addEventListener('click', e => { if (e.target === e.currentTarget) closeEdit(); });

// ═══════════ 欢迎页 ═══════════

function showWelcome() {
  document.getElementById('welcome-overlay').style.display = 'block';
}

function dismissWelcome() {
  document.getElementById('welcome-overlay').style.display = 'none';
  localStorage.setItem('zhanlong_welcomed', '1');
}
