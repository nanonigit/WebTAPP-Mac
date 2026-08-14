const { app, BrowserWindow, shell, session, Menu } = require('electron');
const path = require('path');
const fs = require('fs');

// 1. Load config.json
let config = {
  name: "Web App",
  url: "https://notebooklm.google.com",
  bundleId: "com.webtoapp.generic",
  width: 1200,
  height: 800,
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

  mainWindow = new BrowserWindow({
    width: config.width || 1200,
    height: config.height || 800,
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
  });

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

  // Intercept window close to hide on macOS
  mainWindow.on('close', (event) => {
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
    mainWindow.show();
    if (config.startMaximized) {
      mainWindow.maximize();
    }
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
