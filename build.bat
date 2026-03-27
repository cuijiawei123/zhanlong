@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ==========================================
:: 斩龙 · 一键打包脚本 (Windows)
:: 用法：双击运行，或在项目根目录执行 build.bat
:: ==========================================

echo.
echo  ╔══════════════════════════════════════╗
echo  ║       斩龙 · 一键打包脚本           ║
echo  ╚══════════════════════════════════════╝
echo.

:: 记录开始时间
set START_TIME=%time%

:: ==========================================
:: 0. 环境检查
:: ==========================================
echo [0/5] 环境检查...

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Python，请先安装 Python 3.9+ 并添加到 PATH
    goto :fail
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VER=%%v
echo   ✅ Python %PYTHON_VER%

:: 检查 Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 Node.js，请先安装 Node.js 18+ 并添加到 PATH
    goto :fail
)
for /f "tokens=1 delims=" %%v in ('node --version 2^>^&1') do set NODE_VER=%%v
echo   ✅ Node.js %NODE_VER%

:: 检查 npm
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ 未找到 npm
    goto :fail
)
echo   ✅ npm OK

:: 检查 PyInstaller
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo   ⚠️  PyInstaller 未安装，正在安装...
    pip install pyinstaller -q
    if errorlevel 1 (
        echo ❌ PyInstaller 安装失败
        goto :fail
    )
)
echo   ✅ PyInstaller OK

:: 检查关键文件
if not exist "backend.py" (
    echo ❌ 未找到 backend.py，请确保在项目根目录运行此脚本
    goto :fail
)
if not exist "backend.spec" (
    echo ❌ 未找到 backend.spec
    goto :fail
)
if not exist "electron\package.json" (
    echo ❌ 未找到 electron\package.json
    goto :fail
)

echo   ✅ 项目文件完整
echo.

:: ==========================================
:: 1. 安装 Python 依赖
:: ==========================================
echo [1/5] 安装 Python 依赖...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo ❌ Python 依赖安装失败
    goto :fail
)
pip install websockets -q
echo   ✅ Python 依赖已就绪
echo.

:: ==========================================
:: 2. PyInstaller 打包 Python 后端
:: ==========================================
echo [2/5] 打包 Python 后端 (PyInstaller)...
echo   这可能需要 1-3 分钟...

:: 清理旧产物
if exist "dist\backend" rmdir /s /q "dist\backend" 2>nul
if exist "build\backend" rmdir /s /q "build\backend" 2>nul

pyinstaller backend.spec --noconfirm
if errorlevel 1 (
    echo ❌ PyInstaller 打包失败
    goto :fail
)

:: 验证产物
if not exist "dist\backend\backend.exe" (
    echo ❌ 未生成 backend.exe
    goto :fail
)

:: 统计后端大小
for /f "tokens=3" %%s in ('dir "dist\backend" /s /-c 2^>nul ^| findstr "个文件"') do set BACKEND_SIZE=%%s
echo   ✅ Python 后端打包完成 (dist\backend\)
echo.

:: ==========================================
:: 3. 安装 Electron 依赖
:: ==========================================
echo [3/5] 安装 Electron 依赖...
cd electron
call npm install --prefer-offline 2>nul || call npm install
if errorlevel 1 (
    echo ❌ npm install 失败
    cd ..
    goto :fail
)
echo   ✅ Electron 依赖已就绪
echo.

:: ==========================================
:: 4. Electron-Builder 打包
:: ==========================================
echo [4/5] 打包 Electron 应用 (electron-builder)...
echo   这可能需要 3-5 分钟...

:: 清理旧产物
if exist "release" rmdir /s /q "release" 2>nul

call npm run dist:win
if errorlevel 1 (
    echo ❌ Electron 打包失败
    cd ..
    goto :fail
)

cd ..
echo   ✅ Electron 应用打包完成
echo.

:: ==========================================
:: 5. 验证最终产物
:: ==========================================
echo [5/5] 验证打包产物...

set FOUND=0

:: 查找 NSIS 安装包
for %%f in (electron\release\*.exe) do (
    echo   📦 %%~nxf  (%%~zf bytes)
    set FOUND=1
)

:: 查找 portable
for %%f in (electron\release\*.exe) do (
    rem 已在上面列出
)

if %FOUND%==0 (
    echo ⚠️  未在 electron\release\ 找到安装包
    echo   请检查 electron-builder 日志
) else (
    echo.
    echo ══════════════════════════════════════
    echo  ✅ 打包完成！
    echo ══════════════════════════════════════
    echo.
    echo  产物目录: electron\release\
    echo.
    echo  文件说明:
    echo   • 斩龙 Setup x.x.x.exe  ← NSIS 安装包（推荐分发）
    echo   • 斩龙 x.x.x.exe        ← 便携版（免安装）
    echo.
)

:: 计算耗时
set END_TIME=%time%
echo  开始: %START_TIME%
echo  结束: %END_TIME%
echo.

goto :done

:fail
echo.
echo ══════════════════════════════════════
echo  ❌ 打包失败，请检查上方错误信息
echo ══════════════════════════════════════
echo.

:done
pause
