#!/usr/bin/env bash
# ==========================================
# 斩龙 · 一键打包脚本 (macOS / Linux)
# 用法：chmod +x build.sh && ./build.sh
# ==========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║       斩龙 · 一键打包脚本           ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

START_TIME=$(date +%s)
PLATFORM=$(uname -s)

# ==========================================
# 0. 环境检查
# ==========================================
echo -e "${CYAN}[0/5] 环境检查...${NC}"

# Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ 未找到 python3${NC}"
    exit 1
fi
PYTHON_VER=$(python3 --version 2>&1)
echo -e "  ${GREEN}✅ $PYTHON_VER${NC}"

# Node.js
if ! command -v node &>/dev/null; then
    echo -e "${RED}❌ 未找到 node${NC}"
    exit 1
fi
NODE_VER=$(node --version 2>&1)
echo -e "  ${GREEN}✅ Node.js $NODE_VER${NC}"

# npm
if ! command -v npm &>/dev/null; then
    echo -e "${RED}❌ 未找到 npm${NC}"
    exit 1
fi
echo -e "  ${GREEN}✅ npm OK${NC}"

# PyInstaller
if ! command -v pyinstaller &>/dev/null; then
    echo -e "  ${YELLOW}⚠️  PyInstaller 未安装，正在安装...${NC}"
    pip3 install pyinstaller -q
fi
echo -e "  ${GREEN}✅ PyInstaller OK${NC}"

# 关键文件
if [ ! -f "backend.py" ]; then
    echo -e "${RED}❌ 未找到 backend.py，请确保在项目根目录运行${NC}"
    exit 1
fi
if [ ! -f "backend.spec" ]; then
    echo -e "${RED}❌ 未找到 backend.spec${NC}"
    exit 1
fi
echo -e "  ${GREEN}✅ 项目文件完整${NC}"
echo ""

# ==========================================
# 1. 安装 Python 依赖
# ==========================================
echo -e "${CYAN}[1/5] 安装 Python 依赖...${NC}"
pip3 install -r requirements.txt -q
pip3 install websockets -q
echo -e "  ${GREEN}✅ Python 依赖已就绪${NC}"
echo ""

# ==========================================
# 2. PyInstaller 打包 Python 后端
# ==========================================
echo -e "${CYAN}[2/5] 打包 Python 后端 (PyInstaller)...${NC}"
echo "  这可能需要 1-3 分钟..."

rm -rf dist/backend build/backend 2>/dev/null || true
pyinstaller backend.spec --noconfirm

# 验证
BACKEND_BIN="dist/backend/backend"
if [ "$PLATFORM" = "Darwin" ] || [ "$PLATFORM" = "Linux" ]; then
    if [ ! -f "$BACKEND_BIN" ]; then
        echo -e "${RED}❌ 未生成 backend 可执行文件${NC}"
        exit 1
    fi
fi

BACKEND_SIZE=$(du -sh dist/backend 2>/dev/null | cut -f1)
echo -e "  ${GREEN}✅ Python 后端打包完成 ($BACKEND_SIZE)${NC}"
echo ""

# ==========================================
# 3. 安装 Electron 依赖
# ==========================================
echo -e "${CYAN}[3/5] 安装 Electron 依赖...${NC}"
cd electron
npm install
echo -e "  ${GREEN}✅ Electron 依赖已就绪${NC}"
echo ""

# ==========================================
# 4. Electron-Builder 打包
# ==========================================
echo -e "${CYAN}[4/5] 打包 Electron 应用 (electron-builder)...${NC}"
echo "  这可能需要 3-5 分钟..."

rm -rf release 2>/dev/null || true

if [ "$PLATFORM" = "Darwin" ]; then
    npm run dist:mac
elif [ "$PLATFORM" = "Linux" ]; then
    npm run dist:linux
else
    npm run dist
fi

cd ..
echo -e "  ${GREEN}✅ Electron 应用打包完成${NC}"
echo ""

# ==========================================
# 5. 验证最终产物
# ==========================================
echo -e "${CYAN}[5/5] 验证打包产物...${NC}"

if [ "$PLATFORM" = "Darwin" ]; then
    ls -lh electron/release/*.dmg 2>/dev/null && echo "" || echo -e "  ${YELLOW}⚠️  未找到 .dmg${NC}"
elif [ "$PLATFORM" = "Linux" ]; then
    ls -lh electron/release/*.AppImage 2>/dev/null && echo "" || echo -e "  ${YELLOW}⚠️  未找到 .AppImage${NC}"
fi

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

echo ""
echo "══════════════════════════════════════"
echo -e "  ${GREEN}✅ 打包完成！${NC} (耗时 ${ELAPSED}s)"
echo "══════════════════════════════════════"
echo ""
echo "  产物目录: electron/release/"
echo ""
