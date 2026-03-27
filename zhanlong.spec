# -*- mode: python ; coding: utf-8 -*-
# zhanlong.spec — 斩龙语音宏工具打包配置
#
# 用法（Windows 上执行）：
#   pyinstaller zhanlong.spec
#
# 产物位于 dist/斩龙/ 目录

import os

block_cipher = None

# ==========================================
# 项目根目录
# ==========================================
PROJECT_ROOT = os.path.abspath('.')

# ==========================================
# 需要打包的模型文件（排除未使用的 epoch-99 和 int8 模型，节省约 22MB）
# ==========================================
model_files = [
    # KWS 模型（epoch-12，实际使用的版本）
    ('model/encoder-epoch-12-avg-2-chunk-16-left-64.onnx', 'model'),
    ('model/decoder-epoch-12-avg-2-chunk-16-left-64.onnx', 'model'),
    ('model/joiner-epoch-12-avg-2-chunk-16-left-64.onnx',  'model'),
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
# images 目录（打赏二维码，如果存在的话）
# ==========================================
image_files = []
if os.path.isdir('images'):
    for fname in os.listdir('images'):
        fpath = os.path.join('images', fname)
        if os.path.isfile(fpath):
            image_files.append((fpath, 'images'))

# ==========================================
# 合并所有数据文件
# ==========================================
all_datas = model_files + utils_files + image_files

# ==========================================
# Analysis
# ==========================================
a = Analysis(
    ['main.py'],
    pathex=[PROJECT_ROOT],
    binaries=[],
    datas=all_datas,
    hiddenimports=[
        'sherpa_onnx',
        'sounddevice',
        'pyautogui',
        'numpy',
        'PySide6',
        'PySide6.QtWidgets',
        'PySide6.QtCore',
        'PySide6.QtGui',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除未使用的大包（即使装了也不打包进去）
        'torch', 'torchaudio', 'torchvision',
        'tensorflow', 'tensorboard', 'tensorboardX',
        'mediapipe', 'cv2', 'opencv',
        'faster_whisper', 'whisper',
        'funasr', 'modelscope',
        'matplotlib', 'scipy',
        'sklearn', 'scikit-learn',
        'tkinter',  # 已弃用 tkinter 窗口
        'dearpygui',
        'IPython', 'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ==========================================
# PYZ（Python 字节码压缩包）
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
    name='斩龙',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,          # 启用 UPX 压缩（需安装 UPX）
    console=False,      # 无控制台窗口（GUI 模式）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)

# ==========================================
# COLLECT（收集所有文件到 dist/斩龙/ 目录）
# ==========================================
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='斩龙',
)
