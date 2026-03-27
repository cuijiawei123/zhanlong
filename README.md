# 🐉 斩龙 — 语音宏配置器

> 用声音操控游戏。说一个词，触发一串按键。

斩龙是一个**语音驱动的键盘宏工具**，专为游戏玩家设计。通过语音指令实时触发预设的按键操作，解放你的双手。

![Electron](https://img.shields.io/badge/Electron-33-47848F?logo=electron)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python)
![sherpa-onnx](https://img.shields.io/badge/sherpa--onnx-KWS-FF6F00)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

---

## ✨ 功能特性

- 🎤 **语音识别** — 基于 sherpa-onnx Zipformer 模型，完全本地运行，无需联网
- ⌨️ **按键宏** — 支持单键、组合键（Ctrl+C）、双击、连招等任意按键序列
- 🗣️ **方言适配** — 自动生成平翘舌、前后鼻音等方言变体，提高识别率
- 🎯 **模糊匹配** — 编辑距离兜底，说得不标准也能识别
- 📊 **动态阈值** — 自动检测误触并调高阈值，长期无误触后自动恢复
- 🖥️ **现代 UI** — Electron 前端，暗色主题，支持中英双语
- 📦 **一键打包** — PyInstaller + electron-builder，双击脚本即可打包

## 🎮 使用场景

| 你说... | 触发按键 | 游戏场景 |
|---------|---------|---------|
| "踩" | `W` | 前进/踩地板 |
| "跳" | `C` | 跳跃 |
| "大招" | `R` | 释放大招 |
| "跳刀" | `1` | 使用跳刀 |
| "复制" | `Ctrl+C` | 复制 |
| "点灯" | `R` | 点灯笼 |

所有指令和按键都可以自定义，支持录音自动转拼音。

---

## 🏗️ 架构

```
┌──────────────────┐     WebSocket      ┌──────────────────┐
│  Electron 前端   │ ◄──────────────── │  Python 后端     │
│  (HTML/CSS/JS)   │   ws://127.0.0.1  │  (backend.py)    │
│                  │      :9877         │                  │
│  • 宏管理面板    │                    │  • sherpa-onnx   │
│  • 实时日志      │                    │  • 语音识别 KWS  │
│  • 中英双语      │                    │  • 按键模拟      │
└──────────────────┘                    └──────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+
- 麦克风

### 安装

```bash
# 克隆仓库
git clone https://github.com/cuijiawei123/zhanlong.git
cd zhanlong

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Electron 依赖
cd electron
npm install
```

### 运行

```bash
# 在 electron/ 目录下
npm run dev
```

Electron 会自动启动 Python 后端，打开窗口后即可使用。

### 打包发布

```bash
# Windows
build.bat

# macOS / Linux
chmod +x build.sh && ./build.sh
```

详见 [封装exe.md](封装exe.md)

---

## 📁 项目结构

```
zhanlong/
├── backend.py              # Python WebSocket 后端
├── main.py                 # PySide6 GUI 版本（旧版，保留兼容）
├── electron/
│   ├── src/
│   │   ├── main.js         # Electron 主进程
│   │   └── preload.js      # WebSocket 通信桥接
│   └── public/
│       ├── index.html       # 前端页面
│       ├── app.js           # 前端逻辑
│       └── i18n.js          # 中英双语
├── utils/
│   ├── config_manager.py   # 单例配置管理器
│   ├── voice_listener.py   # 语音监听 (VAD+AGC+KWS)
│   ├── voice_engine.py     # 录音识别引擎
│   ├── dialect_variants.py # 方言变体生成
│   ├── fuzzy_matcher.py    # 模糊匹配
│   ├── threshold_tuner.py  # 动态阈值调优
│   └── skills.json         # 宏配置
├── model/
│   ├── encoder-*.onnx      # Zipformer 编码器
│   ├── decoder-*.onnx      # Zipformer 解码器
│   ├── joiner-*.onnx       # Zipformer 连接器
│   ├── silero_vad.onnx     # VAD 模型
│   ├── tokens.txt          # 词表
│   └── keywords_invoker.txt # 关键词+方言变体+阈值
├── build.bat               # Windows 一键打包
├── build.sh                # macOS/Linux 一键打包
├── backend.spec            # PyInstaller 打包配置 (后端)
├── zhanlong.spec           # PyInstaller 打包配置 (独立GUI)
└── 封装exe.md              # 打包文档
```

## 🧠 语音识别技术栈

| 组件 | 方案 | 说明 |
|------|------|------|
| ASR 模型 | Zipformer (3.3M) | ICLR 2024，WenetSpeech 10000h 训练 |
| 推理框架 | sherpa-onnx | k2-fsa 出品，ONNX Runtime |
| 量化 | int8 | 推理快 2-3x，精度损失 <1% |
| VAD | Silero VAD | 有声段检测，减少无效推理 |
| 增益控制 | 自定义 AGC | 动态增益，max_gain=6 |
| 方言适配 | 规则引擎 | 平翘舌/前后鼻音/l-n/h-f 等 |
| 关键词检测 | 流式 KWS | chunk-16，延迟 ~320ms |

## 🤝 致谢

- [sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) — 新一代 Kaldi 语音识别框架
- [Zipformer](https://arxiv.org/abs/2310.11230) — 小米 Daniel Povey 团队
- [Electron](https://www.electronjs.org/) — 跨平台桌面应用框架
- [robotLiberator/zhanlong](https://github.com/robotLiberator/zhanlong) — 原始项目

## 📄 License

MIT
