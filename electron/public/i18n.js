// i18n.js — 中英文切换

const I18N = {
  zh: {
    // 导航
    nav_home: "控制台",
    nav_macros: "宏列表",
    nav_logs: "监听日志",
    nav_about: "关于与支持",
    sidebar_status: "系统就绪",

    // 首页
    home_protocol: "斩龙协议",
    home_desc: "高级语音宏引擎，为高强度游戏环境打造。低延迟语音识别，实时按键触发。",
    home_start_listen: "开启监听",
    home_goto_macros: "管理宏配置",
    home_orchestration: "编排",
    home_add_macro: "添加新宏",
    home_history: "历史",
    home_view_logs: "查看监听日志",
    home_core_status: "核心状态",
    home_ready: "就绪",
    home_accuracy: "识别准确率",
    home_buffer: "缓冲同步",
    home_stable: "稳定",
    home_engine_active: "语音引擎就绪",
    home_engine_desc: "VAD + KWS 模块已加载",
    home_macro_waiting: "宏接收等待中",
    home_macro_desc: "等待语音触发...",
    home_latency: "延迟",
    home_macro_count: "已配置宏",

    // 监听按钮
    listen_start: "开启监听",
    listen_stop: "停止监听",
    listen_starting: "启动中...",

    // 状态
    status_offline: "未连接",
    status_online: "已连接",
    engine_offline: "引擎未连接",
    engine_online: "语音引擎在线",
    system_ready: "系统就绪",
    system_listening: "监听中",

    // 宏列表页
    macros_title: "已配置的宏",
    macros_subtitle: "语音指令模块",
    macros_empty: "还没有配置语音宏，点击下方按钮添加",
    add_macro: "添加新宏",
    no_voice: "未设置语音",
    no_keys: "未设置按键",

    // 日志页
    log_session: "会话时长",
    log_triggers: "触发次数",
    log_clear: "清空日志",
    log_waiting: "等待信号...",
    log_started: "语音监听已启动",
    log_stopped: "语音监听已停止",
    log_trigger: "触发技能",

    // 关于页
    about_title: "关于 斩龙",
    disclaimer_title: "免责声明",
    disclaimer_body: '本工具仅限学习娱乐交流。使用宏可能被部分反作弊系统检测，<span class="font-bold underline decoration-secondary decoration-2 underline-offset-4">风险由用户自行承担</span>。我们提倡绿色游戏环境。',
    community_title: "社区交流",
    qq_player: "QQ玩家群",
    qq_dev: "QQ开发群",
    video_channel: "视频号",
    support_title: "支持作者",
    support_desc: "如果觉得有用，欢迎请作者喝杯奶茶 ❤️",
    wechat_pay: "微信支付",
    alipay: "支付宝",
    local_image: "（本地图片）",
    launch_btn: "进入主界面",

    // 编辑弹窗
    edit_new_title: "新建语音宏",
    edit_title_prefix: "编辑 —",
    field_name: "01 宏名称",
    field_name_ph: "例如：踩",
    field_keys: "02 录入按键",
    field_keys_ph: "a b c 或 (ctrl,c)",
    field_keys_hint: "支持语法：double_click:space, (ctrl,c)",
    field_voice: "03 录入语音",
    field_voice_ph: "拼音结果...",
    btn_cancel: "取消",
    btn_save: "保存",

    // 话筒状态
    mic_recording: "🎤 录音中...",
    mic_recognizing: "⏳ 识别中...",

    // 提示
    alert_no_name: "请输入名称",
    alert_no_keys: "请输入按键序列",
    alert_save_fail: "保存失败",
    alert_delete_fail: "删除失败",
    confirm_delete: "确定删除「{name}」？",
  },

  en: {
    nav_home: "COMMAND",
    nav_macros: "MACROS",
    nav_logs: "LOGS",
    nav_about: "Support",
    sidebar_status: "SYSTEM READY",

    home_protocol: "Dragon Slayer Protocol",
    home_desc: "Advanced latency suppression and macro orchestration for high-stakes environments. System core stabilized.",
    home_start_listen: "START LISTENING",
    home_goto_macros: "MANAGE MACROS",
    home_orchestration: "Orchestration",
    home_add_macro: "ADD NEW MACRO",
    home_history: "History",
    home_view_logs: "VIEW SYSTEM LOGS",
    home_core_status: "Core Status",
    home_ready: "READY",
    home_accuracy: "Neural Link",
    home_buffer: "Buffer Sync",
    home_stable: "STABLE",
    home_engine_active: "DRAGON_LAYER ACTIVE",
    home_engine_desc: "Global overlay hook injected.",
    home_macro_waiting: "MACRO_RECV WAITING",
    home_macro_desc: "Listening for input triggers...",
    home_latency: "Latency",
    home_macro_count: "Macros",

    listen_start: "Start Listening",
    listen_stop: "Stop Listening",
    listen_starting: "Starting...",

    status_offline: "Offline",
    status_online: "Online",
    engine_offline: "Engine Offline",
    engine_online: "Voice Engine Online",
    system_ready: "System Ready",
    system_listening: "Listening",

    macros_title: "Configured Macros",
    macros_subtitle: "Active Voice Command Modules",
    macros_empty: "No macros configured. Click the button below to add one.",
    add_macro: "Add New Macro",
    no_voice: "No voice set",
    no_keys: "No keys set",

    log_session: "Session Uptime",
    log_triggers: "Total Triggers",
    log_clear: "Clear Log",
    log_waiting: "Waiting for pulse...",
    log_started: "Voice listening started",
    log_stopped: "Voice listening stopped",
    log_trigger: "Triggered",

    about_title: "About ZhanLong",
    disclaimer_title: "Disclaimer",
    disclaimer_body: 'This tool is for learning and entertainment only. Using macros may be detected by anti-cheat systems. <span class="font-bold underline decoration-secondary decoration-2 underline-offset-4">Use at your own risk</span>. We advocate fair gameplay.',
    community_title: "Community",
    qq_player: "QQ Player Group",
    qq_dev: "QQ Dev Group",
    video_channel: "Video Channel",
    support_title: "Support Us",
    support_desc: "If you find this useful, buy us a coffee ❤️",
    wechat_pay: "WeChat Pay",
    alipay: "Alipay",
    local_image: "(Local image)",
    launch_btn: "Launch Interface",

    edit_new_title: "New Voice Macro",
    edit_title_prefix: "Edit —",
    field_name: "01 Macro Name",
    field_name_ph: "e.g. Kick",
    field_keys: "02 Keyboard Mapping",
    field_keys_ph: "a b c or (ctrl,c)",
    field_keys_hint: "Syntax: double_click:space, (ctrl,c)",
    field_voice: "03 Voice Pinyin",
    field_voice_ph: "Pinyin result...",
    btn_cancel: "Cancel",
    btn_save: "Save",

    mic_recording: "🎤 Recording...",
    mic_recognizing: "⏳ Recognizing...",

    alert_no_name: "Please enter a name",
    alert_no_keys: "Please enter key sequence",
    alert_save_fail: "Save failed",
    alert_delete_fail: "Delete failed",
    confirm_delete: 'Delete "{name}"?',
  }
};

let currentLang = localStorage.getItem('zhanlong_lang') || 'zh';

function t(key, params) {
  let text = (I18N[currentLang] && I18N[currentLang][key]) || (I18N.zh[key]) || key;
  if (params) {
    Object.keys(params).forEach(k => {
      text = text.replace(`{${k}}`, params[k]);
    });
  }
  return text;
}

function applyI18n() {
  // 文本内容
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (val) el.innerHTML = val;
  });
  // placeholder
  document.querySelectorAll('[data-placeholder-i18n]').forEach(el => {
    const key = el.getAttribute('data-placeholder-i18n');
    const val = t(key);
    if (val) el.placeholder = val;
  });
  // 语言切换按钮显示另一种语言
  const toggle = document.getElementById('lang-toggle');
  if (toggle) toggle.textContent = currentLang === 'zh' ? 'EN' : '中';
}

function toggleLang() {
  currentLang = currentLang === 'zh' ? 'en' : 'zh';
  localStorage.setItem('zhanlong_lang', currentLang);
  applyI18n();
  // 重新渲染动态内容
  if (typeof renderMacroGrid === 'function') renderMacroGrid();
}

// 页面加载后立即应用
document.addEventListener('DOMContentLoaded', () => {
  applyI18n();
});
