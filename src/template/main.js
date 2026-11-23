const { app, BrowserWindow, shell, session, Menu, screen } = require('electron');
const path = require('path');
const fs = require('fs');

// 1. Load config.json
let config = {
  name: "Web App",
  url: "https://notebooklm.google.com",
  bundleId: "com.webtoapp.generic",
  width: 780,
  height: 923,
  minWidth: 400,
  minHeight: 300,
  titleBarHidden: false,
  startMaximized: false,
  allowExternalLinksInDefaultBrowser: true,
  customCss: null,
  customJs: null
};

try {
  const configPath = path.join(__dirname, 'config.json');
  if (fs.existsSync(configPath)) {
    const raw = fs.readFileSync(configPath, 'utf8');
    config = Object.assign(config, JSON.parse(raw));
  }
} catch (e) {
  console.error("Failed to parse config.json", e);
}

// 2. Set distinct UserData path for complete profile isolation
const isolatedUserData = path.join(app.getPath('appData'), config.bundleId);
app.setPath('userData', isolatedUserData);

function getWindowStatePath() {
  if (!fs.existsSync(isolatedUserData)) {
    fs.mkdirSync(isolatedUserData, { recursive: true });
  }
  return path.join(isolatedUserData, 'window_state.json');
}

function loadSavedWindowBounds() {
  const defaultWidth = Number(config.width) || 780;
  const defaultHeight = Number(config.height) || 923;
  const fallback = { width: defaultWidth, height: defaultHeight, isMaximized: Boolean(config.startMaximized) };
  try {
    const file = getWindowStatePath();
    if (!fs.existsSync(file)) return fallback;
    const saved = JSON.parse(fs.readFileSync(file, 'utf8'));
    const width = Number(saved.width) >= (config.minWidth || 400) ? Number(saved.width) : defaultWidth;
    const height = Number(saved.height) >= (config.minHeight || 300) ? Number(saved.height) : defaultHeight;
    const state = { width, height, isMaximized: Boolean(saved.isMaximized) };

    if (typeof saved.x === 'number' && typeof saved.y === 'number') {
      const displays = screen.getAllDisplays();
      const visible = displays.some((d) => {
        const b = d.bounds;
        return (
          saved.x + width > b.x + 40 &&
          saved.x < b.x + b.width - 40 &&
          saved.y + height > b.y + 40 &&
          saved.y < b.y + b.height - 40
        );
      });
      if (visible) {
        state.x = saved.x;
        state.y = saved.y;
      }
    }
    return state;
  } catch {
    return fallback;
  }
}

function saveWindowBounds(win) {
  if (!win || win.isDestroyed()) return;
  try {
    const isMaximized = win.isMaximized();
    const bounds = isMaximized && win.getNormalBounds ? win.getNormalBounds() : win.getBounds();
    fs.writeFileSync(
      getWindowStatePath(),
      JSON.stringify({ x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height, isMaximized }, null, 2),
      'utf8'
    );
  } catch {
    // Ignore write failure
  }
}

let mainWindow = null;
let isQuitting = false;

function setupMenu(appName, win) {
  const isMac = process.platform === 'darwin';
  const template = [
    ...(isMac ? [{
      label: appName,
      submenu: [
        { role: 'about', label: `About ${appName}` },
        { type: 'separator' },
        { role: 'hide', label: `Hide ${appName}` },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        {
          label: `Quit ${appName}`,
          accelerator: 'CmdOrCtrl+Q',
          click: () => {
            isQuitting = true;
            app.quit();
          }
        }
      ]
    }] : []),
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
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' }
      ]
    },
    {
      label: 'History',
      submenu: [
        {
          label: 'Back',
          accelerator: 'CmdOrCtrl+[',
          click: () => { if (win && !win.isDestroyed() && win.webContents.canGoBack()) win.webContents.goBack(); }
        },
        {
          label: 'Forward',
          accelerator: 'CmdOrCtrl+]',
          click: () => { if (win && !win.isDestroyed() && win.webContents.canGoForward()) win.webContents.goForward(); }
        }
      ]
    },
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        { type: 'separator' },
        {
          label: 'Close Window',
          accelerator: 'CmdOrCtrl+W',
          click: () => {
            if (win && !win.isDestroyed()) {
              win.hide();
            }
          }
        }
      ]
    }
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

function createWindow() {
  const ses = session.fromPartition('persist:' + config.bundleId);

  ses.setPermissionRequestHandler((webContents, permission, callback) => {
    const allowed = ['media', 'notifications', 'camera', 'microphone', 'display-capture', 'clipboard-read'];
    callback(allowed.includes(permission));
  });

  const savedBounds = loadSavedWindowBounds();
  const winOpts = {
    width: savedBounds.width,
    height: savedBounds.height,
    minWidth: config.minWidth || 400,
    minHeight: config.minHeight || 300,
    title: config.name,
    titleBarStyle: config.titleBarHidden ? 'hiddenInset' : 'default',
    trafficLightPosition: config.titleBarHidden ? { x: 14, y: 14 } : undefined,
    show: false,
    webPreferences: {
      session: ses,
      nodeIntegration: false,
      contextIsolation: true,
      spellcheck: true,
      preload: path.join(__dirname, 'preload.js')
    }
  };
  if (typeof savedBounds.x === 'number' && typeof savedBounds.y === 'number') {
    winOpts.x = savedBounds.x;
    winOpts.y = savedBounds.y;
  }

  mainWindow = new BrowserWindow(winOpts);

  let saveTimer = null;
  const scheduleSave = () => {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => saveWindowBounds(mainWindow), 150);
  };
  mainWindow.on('resize', scheduleSave);
  mainWindow.on('move', scheduleSave);

  // Clean User-Agent for Google & Meta OAuth compatibility
  const defaultUA = mainWindow.webContents.userAgent;
  const cleanUA = defaultUA.replace(/Electron\/\S+\s?/, '');
  mainWindow.webContents.userAgent = cleanUA;

  // Sync title and Dock unread badge
  mainWindow.on('page-title-updated', (evt, title) => {
    if (app.dock) {
      const match = title.match(/(?:\(|\[)(\d+\+?)(?:\)|\])/);
      app.dock.setBadge(match ? match[1] : '');
    }
  });

  // Intercept window close to save bounds and hide on macOS
  mainWindow.on('close', (event) => {
    saveWindowBounds(mainWindow);
    if (!isQuitting && process.platform === 'darwin') {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Smart URL and Popup Handler
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    let initialHost = "";
    try {
      initialHost = new URL(config.url).host.toLowerCase();
    } catch(e) {}

    let targetHost = "";
    try {
      targetHost = new URL(url).host.toLowerCase();
    } catch(e) {}

    const authKeywords = [
      'accounts.google.com', 'google.com/accounts', 'google.com/signin',
      'appleid.apple.com', 'login.microsoftonline.com', 'login.live.com',
      'facebook.com', 'meta.com', 'messenger.com', 'github.com/login',
      'auth0.com', 'okta.com', 'clerk.com', 'oauth', 'login', 'signin', 'sso'
    ];
    const isAuthFlow = authKeywords.some(k => targetHost.includes(k) || url.toLowerCase().includes(k));
    const isSameHost = initialHost && (targetHost === initialHost || targetHost.endsWith('.' + initialHost) || initialHost.endsWith('.' + targetHost));

    if (isAuthFlow || isSameHost || url.startsWith('about:') || url.startsWith('blob:')) {
      return {
        action: 'allow',
        overrideBrowserWindowOptions: {
          webPreferences: {
            session: ses,
            nodeIntegration: false,
            contextIsolation: true
          }
        }
      };
    }

    if (config.allowExternalLinksInDefaultBrowser !== false) {
      shell.openExternal(url);
      return { action: 'deny' };
    }

    return { action: 'allow' };
  });

  // Handle top-level external navigation
  mainWindow.webContents.on('will-navigate', (event, navigationUrl) => {
    try {
      const initialHost = new URL(config.url).host.toLowerCase();
      const targetHost = new URL(navigationUrl).host.toLowerCase();
      const isSameHost = targetHost === initialHost || targetHost.endsWith('.' + initialHost) || initialHost.endsWith('.' + targetHost);
      const authKeywords = [
        'accounts.google.com', 'google.com/accounts', 'google.com/signin',
        'appleid.apple.com', 'login.microsoftonline.com', 'login.live.com',
        'facebook.com', 'meta.com', 'messenger.com', 'github.com/login',
        'auth0.com', 'okta.com', 'clerk.com', 'oauth', 'login', 'signin', 'sso'
      ];
      const isAuthFlow = authKeywords.some(k => targetHost.includes(k) || navigationUrl.toLowerCase().includes(k));

      if (!isSameHost && !isAuthFlow && config.allowExternalLinksInDefaultBrowser !== false) {
        event.preventDefault();
        shell.openExternal(navigationUrl);
      }
    } catch (e) {}
  });

  setupMenu(config.name, mainWindow);

  mainWindow.once('ready-to-show', () => {
    if (savedBounds.isMaximized) {
      mainWindow.maximize();
    }
    mainWindow.show();
  });

  mainWindow.loadURL(config.url);
}

app.whenReady().then(() => {
  createWindow();
});

app.on('before-quit', () => {
  isQuitting = true;
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow();
  } else {
    mainWindow.show();
    mainWindow.focus();
  }
});
