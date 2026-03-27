# backend.py — Python WebSocket 后端
# 暴露语音识别、按键模拟、配置管理能力给 Electron 前端

import asyncio
import json
import threading
import re
import sys
import os

# 确保项目根目录在 path 里
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config_manager import ConfigManager
from utils.voice_engine import start_recording, stop_and_get_result
from utils.voice_listener import VoiceListener

try:
    import websockets
except ImportError:
    print("[Backend] Installing websockets...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "websockets", "-q"])
    import websockets


# ==========================================
# 全局状态
# ==========================================

config = ConfigManager()
config.load_config()

listener = None
listener_thread = None
ws_clients = set()  # 所有已连接的前端


# ==========================================
# 向前端推送事件
# ==========================================

def broadcast_event(event_name, data=None):
    """向所有前端推送事件"""
    msg = json.dumps({"type": "event", "event": event_name, "data": data or {}})
    for client in list(ws_clients):
        try:
            asyncio.run_coroutine_threadsafe(client.send(msg), loop)
        except Exception:
            pass


# ==========================================
# 处理前端请求
# ==========================================

async def handle_message(websocket, raw):
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError:
        return

    req_id = msg.get("id")
    action = msg.get("action")

    async def reply(data=None, error=None):
        resp = {"id": req_id}
        if error:
            resp["error"] = str(error)
        else:
            resp["data"] = data or {}
        await websocket.send(json.dumps(resp, ensure_ascii=False))

    try:
        # ── 获取配置 ──
        if action == "get_config":
            macros = config.get_macros_snapshot()
            keywords = config.get_keywords_snapshot()
            all_names = config.get_all_names()

            items = []
            for name in all_names:
                actions = macros.get(name, [])
                voice = keywords.get(name, "")
                # 将 actions 序列化为可读字符串
                keys_str = actions_to_str(actions)
                items.append({"name": name, "voice": voice, "keys": keys_str, "actions": actions})

            await reply({"items": items})

        # ── 保存/更新宏 ──
        elif action == "save_macro":
            name = msg.get("name", "").strip()
            actions_str = msg.get("actions", "").strip()
            voice = msg.get("voice", "").strip()

            if not name:
                await reply(error="名称不能为空")
                return

            actions = parse_user_input(actions_str)
            if actions_str and not actions:
                await reply(error="按键解析失败")
                return

            if actions:
                config.set_macro(name, actions)
            if voice:
                # 清理拼音
                m = re.search(r'\[(.*?)\]', voice)
                clean = " ".join((m.group(1) if m else voice).split())
                if clean:
                    config.set_keyword(name, clean)

            config.save_all()
            await reply({"ok": True})

        # ── 删除宏 ──
        elif action == "delete_macro":
            name = msg.get("name", "").strip()
            config.remove_entry(name)
            config.save_all()
            await reply({"ok": True})

        # ── 开始监听 ──
        elif action == "start_listening":
            global listener, listener_thread
            if listener and listener.is_running:
                await reply({"status": "already_running"})
                return

            listener = VoiceListener(
                on_trigger=lambda n: broadcast_event("trigger", {"name": n}),
                on_status=lambda s: broadcast_event("status", {"status": s})
            )
            listener_thread = threading.Thread(target=listener.start, daemon=True)
            listener_thread.start()
            await reply({"status": "started"})

        # ── 停止监听 ──
        elif action == "stop_listening":
            if listener and listener.is_running:
                listener.stop()
            await reply({"status": "stopped"})

        # ── 获取状态 ──
        elif action == "get_status":
            is_running = listener.is_running if listener else False
            await reply({"listening": is_running})

        # ── 获取触发统计 ──
        elif action == "get_trigger_stats":
            if listener and hasattr(listener, '_tuner'):
                stats = listener._tuner.get_stats()
                await reply({"stats": stats})
            else:
                await reply({"stats": {}})

        # ── 开始录音 ──
        elif action == "start_recording":
            ok = start_recording()
            await reply({"ok": ok})

        # ── 停止录音 ──
        elif action == "stop_recording":
            raw_text, pinyin = stop_and_get_result()
            await reply({"text": raw_text, "pinyin": pinyin})

        else:
            await reply(error=f"Unknown action: {action}")

    except Exception as e:
        await reply(error=str(e))


# ==========================================
# WebSocket 服务
# ==========================================

async def ws_handler(websocket):
    ws_clients.add(websocket)
    print(f"[Backend] Client connected ({len(ws_clients)} total)")
    try:
        async for message in websocket:
            await handle_message(websocket, message)
    except websockets.ConnectionClosed:
        pass
    finally:
        ws_clients.discard(websocket)
        print(f"[Backend] Client disconnected ({len(ws_clients)} total)")


async def main():
    global loop
    loop = asyncio.get_event_loop()

    port = 9877
    async with websockets.serve(ws_handler, "127.0.0.1", port):
        print(f"[Backend] WebSocket server running on ws://127.0.0.1:{port}")
        await asyncio.Future()  # 永远运行


# ==========================================
# 工具函数
# ==========================================

def actions_to_str(actions):
    parts = []
    for a in actions:
        if isinstance(a, (tuple, list)):
            parts.append(f"double_click:{a[1]}" if a[0] == "double_click" else f"({', '.join(a)})")
        else:
            parts.append(str(a))
    return " ".join(parts)


def parse_user_input(text):
    if not text:
        return []
    actions = []
    for part in re.findall(r'\([^)]+\)|\S+', text):
        part = part.strip()
        if not part:
            continue
        if part.startswith('(') and part.endswith(')'):
            keys = [k.strip().strip("'\"") for k in part[1:-1].split(',') if k.strip()]
            if keys:
                actions.append(tuple(keys))
        elif part.startswith("double_click:"):
            actions.append(("double_click", part.split(":", 1)[1].strip().strip("'\"")))
        else:
            actions.append(part.strip("'\""))
    return actions


# ==========================================
# 启动
# ==========================================

if __name__ == "__main__":
    print("[Backend] Starting...")
    asyncio.run(main())
