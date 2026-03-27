// src/main.js — Electron 主进程（无边框窗口 + IPC 窗口控制）
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow = null;
let pythonProcess = null;

// ==========================================
// 启动 Python 后端
// ==========================================

function startPythonBackend() {
  const isDev = process.argv.includes('--dev');
  const fs = require('fs');

  let cmd, args, cwd;

  if (isDev) {
    // ── 开发模式：用源码运行 ──
    const projectRoot = path.resolve(__dirname, '..', '..');
    cwd = projectRoot;

    // 优先使用 venv
    const venvPython = path.join(projectRoot, '.venv', 'bin', 'python');
    const venvPythonWin = path.join(projectRoot, '.venv', 'Scripts', 'python.exe');
    if (fs.existsSync(venvPython)) {
      cmd = venvPython;
    } else if (fs.existsSync(venvPythonWin)) {
      cmd = venvPythonWin;
    } else {
      cmd = process.platform === 'win32' ? 'python' : 'python3';
    }
    args = [path.join(projectRoot, 'backend.py')];
  } else {
    // ── 生产模式：运行 PyInstaller 打包的后端 ──
    const backendDir = path.join(process.resourcesPath, 'backend');
    cwd = backendDir;

    // 跨平台：Windows 是 backend.exe，macOS/Linux 是 backend（无后缀）
    const exeName = process.platform === 'win32' ? 'backend.exe' : 'backend';
    const exePath = path.join(backendDir, exeName);

    if (!fs.existsSync(exePath)) {
      console.error(`[Main] Backend executable not found: ${exePath}`);
      return;
    }

    cmd = exePath;
    args = [];
  }

  console.log(`[Main] Starting Python backend: ${cmd} ${args.join(' ')}`);

  pythonProcess = spawn(cmd, args, {
    cwd: cwd,
    stdio: ['pipe', 'pipe', 'pipe']
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python] ${data.toString().trim()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python ERR] ${data.toString().trim()}`);
  });

  pythonProcess.on('error', (err) => {
    console.error(`[Main] Failed to start backend: ${err.message}`);
    pythonProcess = null;
  });

  pythonProcess.on('close', (code) => {
    console.log(`[Main] Python process exited with code ${code}`);
    pythonProcess = null;
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    // Windows 上 kill() 发 SIGTERM 可能无效，用 taskkill 确保关闭
    if (process.platform === 'win32') {
      try {
        require('child_process').execSync(`taskkill /pid ${pythonProcess.pid} /T /F`, { stdio: 'ignore' });
      } catch (e) {
        // 进程可能已退出
      }
    } else {
      pythonProcess.kill();
    }
    pythonProcess = null;
  }
}

// ==========================================
// 创建窗口（无边框）
// ==========================================

function createWindow() {
  const isMac = process.platform === 'darwin';

  mainWindow = new BrowserWindow({
    width: 1100,
    height: 700,
    minWidth: 800,
    minHeight: 560,
    title: '斩龙',
    backgroundColor: '#131315',
    show: false,
    frame: false,                          // 无边框
    titleBarStyle: 'hidden',               // macOS: 隐藏标题栏但保留交通灯
    trafficLightPosition: { x: -100, y: -100 },  // macOS: 把交通灯移到不可见位置
    transparent: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'public', 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  if (process.argv.includes('--dev')) {
    mainWindow.webContents.openDevTools({ mode: 'detach' });
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ==========================================
// IPC: 窗口控制（前端按钮调用）
// ==========================================

ipcMain.on('window-minimize', () => {
  if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  }
});

ipcMain.on('window-close', () => {
  if (mainWindow) mainWindow.close();
});

// 让前端知道当前平台
ipcMain.handle('get-platform', () => process.platform);

// ==========================================
// 生命周期
// ==========================================

app.whenReady().then(() => {
  startPythonBackend();

  setTimeout(() => {
    createWindow();
  }, 500);
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  app.quit();
});

app.on('before-quit', () => {
  stopPythonBackend();
});
