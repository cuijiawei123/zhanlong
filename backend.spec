# -*- mode: python ; coding: utf-8 -*-
# backend.spec — 斩龙 Python 后端打包配置（供 Electron 调用）
#
# 用法（Windows 上执行）：
#   pyinstaller backend.spec
#
# 产物位于 dist/backend/ 目录，Electron 打包时会将其复制到 resources/backend/

import os
import sys

block_cipher = None
PROJECT_ROOT = os.path.abspath('.')

# ==========================================
# 模型文件（使用 int8 量化版本，体积更小、推理更快）
# ==========================================
model_files = [
    # KWS 模型（epoch-12, int8 量化）
    ('model/encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx', 'model'),
    ('model/decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx', 'model'),
    ('model/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx',  'model'),
    # VAD 模型
    ('model/silero_vad.onnx', 'model'),
    # 配置文件
    ('model/tokens.txt',             'model'),
    ('model/keywords_invoker.txt',   'model'),
]

# ==========================================
# utils 目录（JSON 配置）
# ==========================================
utils_files = [
    ('utils/skills.json', 'utils'),
]

# ==========================================
# 合并所有数据文件
# ==========================================
all_datas = model_files + utils_files

# ==========================================
# Analysis
# ==========================================
a = Analysis(
    ['backend.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=all_datas,
    hiddenimports=[
        'sherpa_onnx',
        'sounddevice',
        'pyautogui',
        'numpy',
        'websockets',
        'websockets.legacy',
        'websockets.legacy.server',
        'asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Electron 模式不需要 PySide6 GUI
        'PySide6', 'PySide6.QtWidgets', 'PySide6.QtCore', 'PySide6.QtGui',
        'shiboken6',
        # 排除未使用的大包
        'torch', 'torchaudio', 'torchvision',
        'tensorflow', 'tensorboard', 'tensorboardX',
        'mediapipe', 'cv2', 'opencv',
        'faster_whisper', 'whisper',
        'funasr', 'modelscope',
        'matplotlib', 'scipy',
        'sklearn', 'scikit-learn',
        'tkinter',
        'dearpygui',
        'IPython', 'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ==========================================
# PYZ
# ==========================================
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ==========================================
# EXE
# ==========================================
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,       # 后端进程需要 console 输出日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ==========================================
# COLLECT
# ==========================================
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='backend',
)
