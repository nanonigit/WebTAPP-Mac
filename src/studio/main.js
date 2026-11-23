const { app, BrowserWindow, ipcMain, dialog, shell, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn, execSync } = require('child_process');

let mainWindow = null;

function getBuildScriptPath() {
  const candidateInternal = path.join(__dirname, 'generator', 'build_app.py');
  if (fs.existsSync(candidateInternal)) {
    return candidateInternal;
  }
  const candidateDev = path.join(__dirname, '..', 'generator', 'build_app.py');
  if (fs.existsSync(candidateDev)) {
    return candidateDev;
  }
  return path.resolve(__dirname, '../../..', 'src', 'generator', 'build_app.py');
}

function getBuildInfo() {
  const buildInfoPath = path.join(__dirname, 'build_info.json');
  if (fs.existsSync(buildInfoPath)) {
    try {
      return JSON.parse(fs.readFileSync(buildInfoPath, 'utf8'));
    } catch {
      // Fallback below
    }
  }
  const repoRoot = resolveRepoRoot();
  let gitSha = 'dev';
  let version = app.getVersion() || '1.1.0';
  if (repoRoot) {
    try {
      gitSha = execSync(`git -C "${repoRoot}" rev-parse --short HEAD`, { encoding: 'utf8' }).trim();
      const count = execSync(`git -C "${repoRoot}" rev-list --count HEAD`, { encoding: 'utf8' }).trim();
      version = `1.1.${count}`;
    } catch {
      // Ignore git errors
    }
  }
  return { version, gitSha, repoPath: repoRoot };
}

function resolveRepoRoot() {
  const candidates = [
    path.resolve(__dirname, '..', '..'),
    path.join(app.getPath('home'), 'Git', 'WebTAPP-Mac')
  ];
  const buildInfoPath = path.join(__dirname, 'build_info.json');
  if (fs.existsSync(buildInfoPath)) {
    try {
      const info = JSON.parse(fs.readFileSync(buildInfoPath, 'utf8'));
      if (info.repoPath) candidates.unshift(info.repoPath);
    } catch {
      // Ignore
    }
  }
  for (const c of candidates) {
    if (c && fs.existsSync(path.join(c, 'src', 'generator', 'build_studio.py'))) {
      return c;
    }
  }
  return null;
}

function resolveInstalledAppBundlePath() {
  // When running from ".../WebTAPP Mac.app/Contents/Resources/app", walk up 3 levels
  const candidateBundle = path.resolve(__dirname, '..', '..', '..');
  if (candidateBundle.endsWith('.app') && fs.existsSync(candidateBundle)) {
    return candidateBundle;
  }
  const sysApps = '/Applications/WebTAPP Mac.app';
  if (fs.existsSync(sysApps)) return sysApps;
  const userApps = path.join(app.getPath('home'), 'Applications', 'WebTAPP Mac.app');
  if (fs.existsSync(userApps)) return userApps;
  return sysApps;
}

function getUpdateStateFilePath() {
  const userDataDir = app.getPath('userData');
  if (!fs.existsSync(userDataDir)) {
    fs.mkdirSync(userDataDir, { recursive: true });
  }
  return path.join(userDataDir, 'update_state.json');
}

function readUpdateState() {
  try {
    const file = getUpdateStateFilePath();
    if (fs.existsSync(file)) {
      return JSON.parse(fs.readFileSync(file, 'utf8'));
    }
  } catch {
    // Ignore
  }
  return { lastUpdateCheckAt: null, lastUpdatedFromVersion: null };
}

function saveUpdateState(patch) {
  try {
    const current = readUpdateState();
    const next = Object.assign({}, current, patch);
    fs.writeFileSync(getUpdateStateFilePath(), JSON.stringify(next, null, 2), 'utf8');
    return next;
  } catch {
    return readUpdateState();
  }
}

function getHistoryFilePath() {
  const userDataDir = app.getPath('userData');
  if (!fs.existsSync(userDataDir)) {
    fs.mkdirSync(userDataDir, { recursive: true });
  }
  return path.join(userDataDir, 'build_history.json');
}

function readBuildHistory() {
  try {
    const file = getHistoryFilePath();
    if (fs.existsSync(file)) {
      return JSON.parse(fs.readFileSync(file, 'utf8'));
    }
  } catch (err) {
    console.error('Failed to read build history:', err);
  }
  return [];
}

function saveBuildHistory(history) {
  try {
    const file = getHistoryFilePath();
    fs.writeFileSync(file, JSON.stringify(history.slice(0, 100), null, 2), 'utf8');
  } catch (err) {
    console.error('Failed to save build history:', err);
  }
}

function appendHistoryItem(item) {
  const history = readBuildHistory();
  history.unshift(item);
  saveBuildHistory(history);
  return history;
}

function getFolderSizeMB(dirPath) {
  let totalBytes = 0;
  function walk(current) {
    let entries;
    try {
      entries = fs.readdirSync(current, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      const fullPath = path.join(current, entry.name);
      try {
        const stat = fs.lstatSync(fullPath);
        if (stat.isSymbolicLink()) continue;
        if (stat.isDirectory()) {
          walk(fullPath);
        } else if (stat.isFile()) {
          totalBytes += stat.size;
        }
      } catch {
        // Ignore inaccessible files
      }
    }
  }
  walk(dirPath);
  return Number((totalBytes / (1024 * 1024)).toFixed(1));
}

function listInstalledWebApps() {
  const appsDir = path.join(app.getPath('home'), 'Applications');
  if (!fs.existsSync(appsDir)) {
    return [];
  }
  const results = [];
  let entries = [];
  try {
    entries = fs.readdirSync(appsDir, { withFileTypes: true });
  } catch {
    return [];
  }

  for (const entry of entries) {
    if (!entry.name.endsWith('.app')) continue;
    const appPath = path.join(appsDir, entry.name);
    const configPath = path.join(appPath, 'Contents', 'Resources', 'app', 'config.json');
    if (fs.existsSync(configPath)) {
      try {
        const config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
        const stat = fs.statSync(appPath);
        results.push({
          name: config.name || entry.name.replace(/\.app$/, ''),
          url: config.url || '',
          bundleId: config.bundleId || '',
          width: config.width || 1200,
          height: config.height || 800,
          titleBarHidden: Boolean(config.titleBarHidden),
          startMaximized: Boolean(config.startMaximized),
          path: appPath,
          updatedAt: stat.mtime.toISOString(),
          sizeMB: getFolderSizeMB(appPath)
        });
      } catch {
        // Skip invalid config.json
      }
    }
  }

  results.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
  return results;
}

function checkRuntimeEnvironment() {
  const checks = [];

  // 1. Python 3
  try {
    const pyVer = execSync('python3 --version', { encoding: 'utf8' }).trim();
    checks.push({
      id: 'python3',
      name: 'Python 3 Package Builder',
      ok: true,
      detail: pyVer
    });
  } catch (err) {
    checks.push({
      id: 'python3',
      name: 'Python 3 Package Builder',
      ok: false,
      detail: err.message
    });
  }

  // 2. Embedded Chromium / Electron Base Runtime
  const scriptPath = getBuildScriptPath();
  const baseCandidates = [
    path.join(__dirname, 'electron-base', 'Electron.app'),
    path.resolve(__dirname, '..', '..', 'node_modules', 'electron', 'dist', 'Electron.app'),
    path.resolve(path.dirname(scriptPath), '..', '..', 'node_modules', 'electron', 'dist', 'Electron.app')
  ];
  const foundBase = baseCandidates.find((p) => fs.existsSync(p));
  checks.push({
    id: 'chromium-base',
    name: 'Embedded Chromium Runtime (Electron.app)',
    ok: Boolean(foundBase),
    detail: foundBase ? `Chromium ${process.versions.chrome} / Electron ${process.versions.electron}` : 'Not Found'
  });

  // 3. macOS sips & iconutil
  try {
    const sipsPath = execSync('which sips', { encoding: 'utf8' }).trim();
    const iconutilPath = execSync('which iconutil', { encoding: 'utf8' }).trim();
    checks.push({
      id: 'icon-toolchain',
      name: 'macOS Icon Toolchain (sips + iconutil)',
      ok: Boolean(sipsPath && iconutilPath),
      detail: `${sipsPath} · ${iconutilPath}`
    });
  } catch (err) {
    checks.push({
      id: 'icon-toolchain',
      name: 'macOS Icon Toolchain (sips + iconutil)',
      ok: false,
      detail: err.message
    });
  }

  // 4. macOS codesign & xattr (Gatekeeper Ad-Hoc Signing)
  try {
    const codesignPath = execSync('which codesign', { encoding: 'utf8' }).trim();
    checks.push({
      id: 'codesign',
      name: 'Gatekeeper Ad-Hoc Code Signing (codesign + xattr)',
      ok: Boolean(codesignPath),
      detail: codesignPath
    });
  } catch (err) {
    checks.push({
      id: 'codesign',
      name: 'Gatekeeper Ad-Hoc Code Signing (codesign + xattr)',
      ok: false,
      detail: err.message
    });
  }

  // 5. User Applications Directory (~/Applications)
  const userAppsDir = path.join(app.getPath('home'), 'Applications');
  try {
    if (!fs.existsSync(userAppsDir)) {
      fs.mkdirSync(userAppsDir, { recursive: true });
    }
    fs.accessSync(userAppsDir, fs.constants.W_OK);
    checks.push({
      id: 'apps-dir',
      name: 'Install Destination (~/Applications)',
      ok: true,
      detail: userAppsDir
    });
  } catch (err) {
    checks.push({
      id: 'apps-dir',
      name: 'Install Destination (~/Applications)',
      ok: false,
      detail: err.message
    });
  }

  const buildInfo = getBuildInfo();
  const updateState = readUpdateState();

  return {
    version: buildInfo.version,
    gitSha: buildInfo.gitSha,
    versionDisplay: `v${buildInfo.version} (${buildInfo.gitSha})`,
    lastUpdateCheckAt: updateState.lastUpdateCheckAt,
    lastUpdatedFromVersion: updateState.lastUpdatedFromVersion,
    electron: process.versions.electron,
    chromium: process.versions.chrome,
    node: process.versions.node,
    platform: `${process.platform} (${process.arch})`,
    appsDir: userAppsDir,
    checks
  };
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1120,
    height: 780,
    minWidth: 940,
    minHeight: 640,
    title: 'WebTAPP Mac',
    backgroundColor: '#08090a',
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    show: false
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  setupMenu();
}

function setupMenu() {
  const template = [
    {
      label: 'WebTAPP Mac',
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' }
      ]
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' }
      ]
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { type: 'separator' },
        { role: 'toggleDevTools' }
      ]
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        { type: 'separator' },
        { role: 'close' }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// IPC Handlers
ipcMain.handle('select-icon-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Application Icon',
    properties: ['openFile'],
    filters: [
      { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'icns', 'ico', 'webp'] }
    ]
  });

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('select-output-dir', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: 'Select Output Folder',
    properties: ['openDirectory', 'createDirectory']
  });

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

ipcMain.handle('show-in-finder', (event, filePath) => {
  if (filePath) {
    shell.showItemInFolder(filePath);
  }
});

ipcMain.handle('launch-app', async (event, appPath) => {
  if (appPath && fs.existsSync(appPath)) {
    const err = await shell.openPath(appPath);
    return { success: !err, error: err || null };
  }
  return { success: false, error: 'Application bundle not found' };
});

ipcMain.handle('delete-app', async (event, appPath) => {
  if (!appPath || !fs.existsSync(appPath)) {
    return { success: false, error: 'Application not found' };
  }
  try {
    await shell.trashItem(appPath);
    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('list-installed-apps', async () => {
  return listInstalledWebApps();
});

ipcMain.handle('get-runtime-status', async () => {
  return checkRuntimeEnvironment();
});

ipcMain.handle('get-build-history', async () => {
  return readBuildHistory();
});

ipcMain.handle('clear-build-history', async () => {
  saveBuildHistory([]);
  return [];
});

ipcMain.handle('update-app', async () => {
  return new Promise((resolve) => {
    const repoRoot = resolveRepoRoot();
    if (!repoRoot) {
      resolve({
        success: false,
        exitCode: 1,
        status: 'error',
        message: 'WebTAPP-Mac リポジトリが見つかりませんでした。'
      });
      return;
    }

    const updaterCandidates = [
      path.join(__dirname, 'generator', 'update_mac_app.sh'),
      path.join(repoRoot, 'src', 'generator', 'update_mac_app.sh')
    ];
    const updaterPath = updaterCandidates.find((p) => fs.existsSync(p));
    if (!updaterPath) {
      resolve({
        success: false,
        exitCode: 1,
        status: 'error',
        message: 'update_mac_app.sh が見つかりませんでした。'
      });
      return;
    }

    const buildInfo = getBuildInfo();
    const currentDisplay = `v${buildInfo.version} (${buildInfo.gitSha})`;
    const installedApp = resolveInstalledAppBundlePath();

    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send(
        'build-log',
        `\n=== [Self-Update] Current: ${currentDisplay} · Repo: ${repoRoot} ===\n`
      );
    }

    const proc = spawn('/bin/zsh', [updaterPath, buildInfo.gitSha, installedApp], {
      cwd: repoRoot,
      env: process.env
    });

    let stdoutText = '';
    let stderrText = '';

    proc.stdout.on('data', (data) => {
      const chunk = data.toString();
      stdoutText += chunk;
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('build-log', chunk);
      }
    });

    proc.stderr.on('data', (data) => {
      const chunk = data.toString();
      stderrText += chunk;
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('build-log', chunk);
      }
    });

    proc.on('close', (code) => {
      const checkedAt = new Date().toISOString();
      if (code === 0 || code === 10 || code === 11) {
        saveUpdateState({ lastUpdateCheckAt: checkedAt });
      }

      if (code === 0) {
        saveUpdateState({
          lastUpdateCheckAt: checkedAt,
          lastUpdatedFromVersion: currentDisplay
        });
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('build-log', '\n[+] アップデート完了・再起動中...\n');
        }
        resolve({
          success: true,
          exitCode: 0,
          status: 'updated',
          checkedAt,
          message: `アップデート完了 (${currentDisplay} → 最新版)・再起動中...`
        });
        setTimeout(() => {
          spawn('/bin/zsh', ['-c', 'sleep 1 && /usr/bin/open "$1"', 'webtapp-relaunch', installedApp], {
            detached: true,
            stdio: 'ignore'
          }).unref();
          app.quit();
        }, 600);
      } else if (code === 10) {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('build-log', `\n[✓] すでに最新版です (${currentDisplay})\n`);
        }
        resolve({
          success: true,
          exitCode: 10,
          status: 'up_to_date',
          checkedAt,
          message: `すでに最新版です (${currentDisplay})`
        });
      } else if (code === 11) {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('build-log', `\n[i] 現在の修正を含む更新版はまだありません (${currentDisplay})\n`);
        }
        resolve({
          success: true,
          exitCode: 11,
          status: 'ahead_or_unverified',
          checkedAt,
          message: '現在の修正を含む更新版はまだありません。'
        });
      } else {
        const errMsg = (stderrText || stdoutText || `exit ${code}`).trim();
        resolve({
          success: false,
          exitCode: code,
          status: 'error',
          checkedAt,
          message: `アップデートに失敗しました (exit ${code}): ${errMsg}`
        });
      }
    });
  });
});

ipcMain.handle('build-app', async (event, params) => {
  return new Promise((resolve) => {
    const pythonScript = getBuildScriptPath();
    const args = [
      pythonScript,
      '--name', params.name,
      '--url', params.url
    ];

    if (params.icon) {
      args.push('--icon', params.icon);
    }
    if (params.icon_preset) {
      args.push('--icon-preset', params.icon_preset);
    }
    if (params.bundle_id) {
      args.push('--bundle-id', params.bundle_id);
    }
    if (params.width) {
      args.push('--width', String(params.width));
    }
    if (params.height) {
      args.push('--height', String(params.height));
    }
    if (params.hidden_titlebar) {
      args.push('--hidden-titlebar');
    }
    if (params.maximized) {
      args.push('--maximized');
    }
    if (params.install) {
      args.push('--install');
    } else if (params.output_dir) {
      args.push('--output', params.output_dir);
    }

    const startedAt = new Date().toISOString();
    const pyProc = spawn('python3', args, {
      cwd: path.dirname(pythonScript),
      env: process.env
    });

    let output = '';
    let errorOutput = '';

    pyProc.stdout.on('data', (data) => {
      const chunk = data.toString();
      output += chunk;
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('build-log', chunk);
      }
    });

    pyProc.stderr.on('data', (data) => {
      const chunk = data.toString();
      errorOutput += chunk;
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('build-log', chunk);
      }
    });

    pyProc.on('close', (code) => {
      if (code === 0) {
        const match = output.match(/App Path\s*:\s*(.*)/);
        const bundleMatch = output.match(/Bundle ID\s*:\s*(.*)/);
        const appPath = match
          ? match[1].trim()
          : (params.install
              ? path.join(app.getPath('home'), 'Applications', `${params.name}.app`)
              : path.join(params.output_dir || process.cwd(), `${params.name}.app`));
        const bundleId = bundleMatch ? bundleMatch[1].trim() : (params.bundle_id || '');
        appendHistoryItem({
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          name: params.name,
          url: params.url,
          bundleId,
          path: appPath,
          hiddenTitlebar: Boolean(params.hidden_titlebar),
          timestamp: startedAt,
          succeeded: true,
          errorMessage: null
        });
        resolve({ success: true, path: appPath, bundleId, log: output });
      } else {
        const errMsg = (errorOutput || output || `Process exited with code ${code}`).trim();
        appendHistoryItem({
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          name: params.name,
          url: params.url,
          bundleId: params.bundle_id || '',
          path: null,
          hiddenTitlebar: Boolean(params.hidden_titlebar),
          timestamp: startedAt,
          succeeded: false,
          errorMessage: errMsg
        });
        resolve({ success: false, error: errMsg, log: output + '\n' + errorOutput });
      }
    });
  });
});

app.whenReady().then(() => {
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
