// src/preload.js — 安全桥接，暴露后端 API 给前端
const { contextBridge, ipcRenderer } = require('electron');

// ==========================================
// WebSocket 连接管理（含自动重连）
// ==========================================
let ws = null;
let messageHandlers = new Map();
let requestId = 0;
let wsUrl = 'ws://127.0.0.1:9877';
let reconnectTimer = null;
let isConnecting = false;

// 重连配置
const RECONNECT_INTERVAL = 1000;   // 重连间隔（ms）
const MAX_RECONNECT_TRIES = 30;    // 最多重试次数（30秒）
let reconnectTries = 0;

function connect(url) {
  if (url) wsUrl = url;
  reconnectTries = 0;
  return _doConnect();
}

function _doConnect() {
  if (isConnecting) return Promise.resolve();
  isConnecting = true;

  return new Promise((resolve, reject) => {
    try {
      ws = new WebSocket(wsUrl);
    } catch (e) {
      isConnecting = false;
      _scheduleReconnect();
      reject(e);
      return;
    }

    ws.onopen = () => {
      console.log('[WS] Connected to Python backend');
      isConnecting = false;
      reconnectTries = 0;
      // 通知前端连接状态
      if (eventCallbacks['connection']) {
        eventCallbacks['connection'].forEach(cb => cb({ connected: true }));
      }
      resolve();
    };

    ws.onerror = (err) => {
      console.error('[WS] Connection error');
      isConnecting = false;
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected');
      ws = null;
      isConnecting = false;
      // 通知前端连接状态
      if (eventCallbacks['connection']) {
        eventCallbacks['connection'].forEach(cb => cb({ connected: false }));
      }
      // 自动重连
      _scheduleReconnect();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        // 响应式消息（有 id 的是请求响应）
        if (msg.id && messageHandlers.has(msg.id)) {
          messageHandlers.get(msg.id)(msg);
          messageHandlers.delete(msg.id);
        }

        // 推送式消息（事件通知）
        if (msg.type === 'event' && eventCallbacks[msg.event]) {
          eventCallbacks[msg.event].forEach(cb => cb(msg.data));
        }
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    // 首次连接如果 3 秒内没成功，也不阻塞前端启动
    setTimeout(() => {
      if (isConnecting) {
        isConnecting = false;
        resolve(); // 不 reject，让前端正常渲染，后续自动重连
      }
    }, 3000);
  });
}

function _scheduleReconnect() {
  if (reconnectTimer) return;
  if (reconnectTries >= MAX_RECONNECT_TRIES) {
    console.error('[WS] Max reconnect attempts reached, giving up');
    return;
  }

  reconnectTries++;
  console.log(`[WS] Reconnecting in ${RECONNECT_INTERVAL}ms (attempt ${reconnectTries}/${MAX_RECONNECT_TRIES})...`);

  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    _doConnect().catch(() => {}); // 静默处理，重连失败会继续调度
  }, RECONNECT_INTERVAL);
}

function send(action, data = {}) {
  return new Promise((resolve, reject) => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      reject(new Error('WebSocket not connected'));
      return;
    }

    const id = `req_${++requestId}`;
    const msg = { id, action, ...data };

    messageHandlers.set(id, (response) => {
      if (response.error) {
        reject(new Error(response.error));
      } else {
        resolve(response.data);
      }
    });

    // 5秒超时
    setTimeout(() => {
      if (messageHandlers.has(id)) {
        messageHandlers.delete(id);
        reject(new Error('Request timeout'));
      }
    }, 5000);

    ws.send(JSON.stringify(msg));
  });
}

// 事件订阅
const eventCallbacks = {};

function onEvent(eventName, callback) {
  if (!eventCallbacks[eventName]) {
    eventCallbacks[eventName] = [];
  }
  eventCallbacks[eventName].push(callback);
}

// ==========================================
// 暴露给前端的 API
// ==========================================

contextBridge.exposeInMainWorld('api', {
  // 连接后端
  connect,

  // 配置管理
  getConfig: () => send('get_config'),
  saveMacro: (name, actions, voice) => send('save_macro', { name, actions, voice }),
  deleteMacro: (name) => send('delete_macro', { name }),

  // 监听控制
  startListening: () => send('start_listening'),
  stopListening: () => send('stop_listening'),
  getListeningStatus: () => send('get_status'),

  // 录音
  startRecording: () => send('start_recording'),
  stopRecording: () => send('stop_recording'),

  // 事件订阅
  onTrigger: (cb) => onEvent('trigger', cb),       // 语音触发技能
  onStatus: (cb) => onEvent('status', cb),          // 监听状态变化
  onLog: (cb) => onEvent('log', cb),                // 日志推送
  onConnection: (cb) => onEvent('connection', cb),  // 连接状态变化

  // 窗口控制
  windowMinimize: () => ipcRenderer.send('window-minimize'),
  windowMaximize: () => ipcRenderer.send('window-maximize'),
  windowClose: () => ipcRenderer.send('window-close'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
});
