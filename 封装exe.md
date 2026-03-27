# 打包说明

斩龙有两种运行模式，打包方式不同：

---

## 模式一：Electron + Python 后端（推荐）

### 前提条件
- Windows 10/11 x64
- Python 3.9+ 已安装，且在 PATH 中
- Node.js 18+ 已安装
- 已安装项目依赖：`pip install -r requirements.txt`

### 第一步：打包 Python 后端

```bash
# 在项目根目录执行
pyinstaller backend.spec
```

产物位于 `dist/backend/` 目录，包含 `backend.exe` 及所有依赖。

### 第二步：打包 Electron 应用

```bash
cd electron
npm install
npm run dist:win
```

产物位于 `electron/release/` 目录：
- `斩龙 Setup x.x.x.exe` — NSIS 安装包（推荐分发）
- `斩龙 x.x.x.exe` — 便携版（免安装）

### 原理说明

```
electron/release/斩龙.exe
  └── resources/
       ├── app.asar          ← Electron 前端（HTML/CSS/JS）
       └── backend/           ← PyInstaller 打包的 Python 后端
            ├── backend.exe
            ├── model/         ← 语音模型
            └── utils/         ← 配置文件
```

electron-builder 的 `extraResources` 配置会自动将 `dist/backend/` 复制到 `resources/backend/`。

---

## 模式二：PySide6 独立桌面应用（旧版）

如果不需要 Electron 前端，可以直接打包 PySide6 GUI 版本：

```bash
pyinstaller zhanlong.spec
```

产物在 `dist/斩龙/` 目录，双击 `斩龙.exe` 运行。

> ⚠️ 此模式使用旧版 GUI，不包含 Electron 的新 UI 设计。

---

## 注意事项

1. **必须在 Windows 上打包**（`--add-data` 分隔符为 `;`，且依赖 pywin32）
2. **先打 Python 后端，再打 Electron**（Electron 打包时需要 `dist/backend/` 目录存在）
3. 如需 UPX 压缩，先安装 [UPX](https://upx.github.io/) 并确保在 PATH 中
4. `backend.spec` 使用 **int8 量化模型**（体积更小），排除了 PySide6（不需要）
5. 打包前确认 `websockets` 已安装：`pip install websockets`

## 预估体积

| 组件 | 大小 |
|------|------|
| Python 后端（backend.exe + 依赖） | ~80-120MB |
| Electron 前端 | ~180-200MB |
| **安装包总计** | ~250-300MB |

> 体积主要来自 Electron 框架（~150MB）和 sherpa-onnx 运行时（~50MB）。
