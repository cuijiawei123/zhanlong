// src/preload.js — 安全桥接，暴露后端 API 给前端
const { contextBridge, ipcRenderer } = require('electron');

// WebSocket 连接管理
let ws = null;
let messageHandlers = new Map();
let requestId = 0;

function connect(url = 'ws://127.0.0.1:9877') {
  return new Promise((resolve, reject) => {
    ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('[WS] Connected to Python backend');
      resolve();
    };

    ws.onerror = (err) => {
      console.error('[WS] Connection error');
      reject(err);
    };

    ws.onclose = () => {
      console.log('[WS] Disconnected');
      ws = null;
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
  });
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

  // 窗口控制
  windowMinimize: () => ipcRenderer.send('window-minimize'),
  windowMaximize: () => ipcRenderer.send('window-maximize'),
  windowClose: () => ipcRenderer.send('window-close'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
});
