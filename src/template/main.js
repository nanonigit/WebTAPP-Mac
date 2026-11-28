const { app, BrowserWindow, WebContentsView, Notification, shell, session, Menu, screen, ipcMain } = require('electron');
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

const TITLEBAR_HEIGHT = 34;

let mainWindow = null;
let contentWebView = null;
let isQuitting = false;
let lastWebNotificationAt = 0;

function focusMainWindow() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  if (mainWindow.isMinimized()) {
    mainWindow.restore();
  }
  mainWindow.show();
  mainWindow.focus();
}

function showNativeNotification({ title, body, silent = false } = {}) {
  if (!Notification.isSupported()) return;
  try {
    const notif = new Notification({
      title: (title && String(title).trim()) || config.name || 'WebTAPP',
      body: body ? String(body) : '',
      silent: Boolean(silent)
    });
    notif.on('click', () => {
      focusMainWindow();
    });
    notif.show();
  } catch (err) {
    console.error('Failed to show notification:', err);
  }
}

function getActiveWebContents() {
  if (contentWebView && contentWebView.webContents && !contentWebView.webContents.isDestroyed()) {
    return contentWebView.webContents;
  }
  if (mainWindow && !mainWindow.isDestroyed()) {
    return mainWindow.webContents;
  }
  return null;
}

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
        {
          label: 'Reload',
          accelerator: 'CmdOrCtrl+R',
          click: () => { const wc = getActiveWebContents(); if (wc) wc.reload(); }
        },
        {
          label: 'Force Reload',
          accelerator: 'CmdOrCtrl+Shift+R',
          click: () => { const wc = getActiveWebContents(); if (wc) wc.reloadIgnoringCache(); }
        },
        { type: 'separator' },
        {
          label: 'Actual Size',
          accelerator: 'CmdOrCtrl+0',
          click: () => { const wc = getActiveWebContents(); if (wc) wc.setZoomLevel(0); }
        },
        {
          label: 'Zoom In',
          accelerator: 'CmdOrCtrl+Plus',
          click: () => { const wc = getActiveWebContents(); if (wc) wc.setZoomLevel(wc.getZoomLevel() + 0.5); }
        },
        {
          label: 'Zoom Out',
          accelerator: 'CmdOrCtrl+-',
          click: () => { const wc = getActiveWebContents(); if (wc) wc.setZoomLevel(wc.getZoomLevel() - 0.5); }
        },
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
          click: () => { const wc = getActiveWebContents(); if (wc && wc.canGoBack()) wc.goBack(); }
        },
        {
          label: 'Forward',
          accelerator: 'CmdOrCtrl+]',
          click: () => { const wc = getActiveWebContents(); if (wc && wc.canGoForward()) wc.goForward(); }
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

function attachWebContentsHandlers(wc, ses) {
  // Clean User-Agent for Google & Meta OAuth compatibility
  const defaultUA = wc.userAgent;
  const cleanUA = defaultUA.replace(/Electron\/\S+\s?/, '');
  wc.userAgent = cleanUA;

  // Patch window.Notification in the page context so web notifications route to native macOS Notification
  wc.on('dom-ready', () => {
    wc.executeJavaScript(`
      (() => {
        if (window.__webtappNotificationPatched) return;
        const notifyBridge = window.__webtappNotify;
        if (typeof notifyBridge !== 'function') return;
        window.__webtappNotificationPatched = true;

        class WebTAPPNotification {
          constructor(title, options = {}) {
            this.title = String(title || '');
            this.body = options && options.body ? String(options.body) : '';
            this.silent = Boolean(options && options.silent);
            this.tag = options && options.tag ? String(options.tag) : '';
            this.onclick = null;
            this.onclose = null;
            this.onerror = null;
            this.onshow = null;
            try {
              notifyBridge({ title: this.title, body: this.body, silent: this.silent, tag: this.tag });
            } catch {}
          }
          close() {}
          addEventListener() {}
          removeEventListener() {}
          dispatchEvent() { return true; }
        }
        WebTAPPNotification.permission = 'granted';
        WebTAPPNotification.maxActions = 2;
        WebTAPPNotification.requestPermission = (cb) => {
          if (typeof cb === 'function') {
            try { cb('granted'); } catch {}
          }
          return Promise.resolve('granted');
        };

        try {
          Object.defineProperty(window, 'Notification', {
            value: WebTAPPNotification,
            writable: true,
            configurable: true
          });
        } catch {
          window.Notification = WebTAPPNotification;
        }
      })();
    `, true).catch(() => {});
  });

  // Sync title, Dock unread badge, and fallback macOS notification on unread increase
  let previousUnreadCount = null;
  wc.on('did-finish-load', () => {
    const initialMatch = (wc.getTitle() || '').match(/(?:\(|\[)(\d+)(?:\+)?(?:\)|\])/);
    previousUnreadCount = initialMatch ? parseInt(initialMatch[1], 10) : 0;
  });

  wc.on('page-title-updated', (_evt, title) => {
    if (mainWindow && !mainWindow.isDestroyed() && title) {
      mainWindow.setTitle(title);
    }
    const match = title.match(/(?:\(|\[)(\d+\+?)(?:\)|\])/);
    if (app.dock) {
      app.dock.setBadge(match ? match[1] : '');
    }

    const numericMatch = title.match(/(?:\(|\[)(\d+)(?:\+)?(?:\)|\])/);
    const currentUnread = numericMatch ? parseInt(numericMatch[1], 10) : 0;
    const isWindowInactive = !mainWindow || mainWindow.isDestroyed() || !mainWindow.isVisible() || !mainWindow.isFocused();
    const recentlyNotifiedByWeb = Date.now() - lastWebNotificationAt < 3000;

    if (previousUnreadCount !== null && currentUnread > previousUnreadCount && isWindowInactive && !recentlyNotifiedByWeb) {
      showNativeNotification({
        title: config.name,
        body: title
      });
    }
    previousUnreadCount = currentUnread;
  });

  // Smart URL and Popup Handler
  wc.setWindowOpenHandler(({ url }) => {
    let initialHost = "";
    try {
      initialHost = new URL(config.url).host.toLowerCase();
    } catch (e) {}

    let targetHost = "";
    try {
      targetHost = new URL(url).host.toLowerCase();
    } catch (e) {}

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
  wc.on('will-navigate', (event, navigationUrl) => {
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
}

function createWindow() {
  const ses = session.fromPartition('persist:' + config.bundleId);

  const allowedPermissions = new Set(['media', 'notifications', 'camera', 'microphone', 'display-capture', 'clipboard-read']);
  ses.setPermissionRequestHandler((_webContents, permission, callback) => {
    callback(allowedPermissions.has(permission));
  });
  ses.setPermissionCheckHandler((_webContents, permission) => {
    return allowedPermissions.has(permission);
  });

  const savedBounds = loadSavedWindowBounds();
  // Use native BrowserWindow directly (avoid WebContentsView child view which breaks macOS IME & scrolling,
  // and use standard titlebar so traffic lights never overlap page UI buttons).
  const useInsetDragShell = false;

  const winOpts = {
    width: savedBounds.width,
    height: savedBounds.height,
    minWidth: config.minWidth || 400,
    minHeight: config.minHeight || 300,
    title: config.name,
    backgroundColor: '#181818',
    titleBarStyle: useInsetDragShell ? 'hiddenInset' : 'default',
    trafficLightPosition: useInsetDragShell ? { x: 14, y: 11 } : undefined,
    show: false,
    webPreferences: useInsetDragShell
      ? {
          nodeIntegration: false,
          contextIsolation: true
        }
      : {
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

  // Intercept window close to save bounds and hide on macOS
  mainWindow.on('close', (event) => {
    saveWindowBounds(mainWindow);
    if (!isQuitting && process.platform === 'darwin') {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    contentWebView = null;
    mainWindow = null;
  });

  setupMenu(config.name, mainWindow);

  if (useInsetDragShell) {
    // Load minimal draggable titlebar shell so traffic lights never overlap page buttons
    const titlebarHtml = `<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><style>
  html, body {
    margin: 0; padding: 0; width: 100%; height: 100%;
    background: #181818;
    overflow: hidden;
    transition: background-color 150ms ease;
  }
  .drag-bar {
    position: fixed; left: 0; right: 0; top: 0; height: ${TITLEBAR_HEIGHT}px;
    -webkit-app-region: drag;
  }
  .sep {
    position: fixed; left: 0; right: 0; top: ${TITLEBAR_HEIGHT - 1}px; height: 1px;
    background: rgba(128, 128, 128, 0.14);
    pointer-events: none;
  }
</style></head>
<body><div class="drag-bar"></div><div class="sep"></div></body>
</html>`;
    mainWindow.loadURL('data:text/html;charset=utf-8,' + encodeURIComponent(titlebarHtml));

    contentWebView = new WebContentsView({
      webPreferences: {
        session: ses,
        nodeIntegration: false,
        contextIsolation: true,
        spellcheck: true,
        preload: path.join(__dirname, 'preload.js')
      }
    });
    mainWindow.contentView.addChildView(contentWebView);

    const updateViewBounds = () => {
      if (!mainWindow || mainWindow.isDestroyed() || !contentWebView) return;
      const [cw, ch] = mainWindow.getContentSize();
      const topOffset = mainWindow.isFullScreen() ? 0 : TITLEBAR_HEIGHT;
      contentWebView.setBounds({
        x: 0,
        y: topOffset,
        width: Math.max(100, cw),
        height: Math.max(100, ch - topOffset)
      });
    };

    updateViewBounds();
    mainWindow.on('resize', updateViewBounds);
    mainWindow.on('enter-full-screen', updateViewBounds);
    mainWindow.on('leave-full-screen', updateViewBounds);
    mainWindow.on('focus', () => {
      if (contentWebView && contentWebView.webContents && !contentWebView.webContents.isDestroyed()) {
        contentWebView.webContents.focus();
      }
    });

    attachWebContentsHandlers(contentWebView.webContents, ses);

    mainWindow.once('ready-to-show', () => {
      updateViewBounds();
      if (savedBounds.isMaximized) {
        mainWindow.maximize();
      }
      mainWindow.show();
      contentWebView.webContents.focus();
    });

    contentWebView.webContents.loadURL(config.url);
  } else {
    attachWebContentsHandlers(mainWindow.webContents, ses);

    mainWindow.once('ready-to-show', () => {
      if (savedBounds.isMaximized) {
        mainWindow.maximize();
      }
      mainWindow.show();
    });

    mainWindow.loadURL(config.url);
  }
}

ipcMain.on('show-notification', (_event, payload) => {
  if (!payload || typeof payload !== 'object') return;
  lastWebNotificationAt = Date.now();
  showNativeNotification({
    title: payload.title,
    body: payload.body,
    silent: payload.silent
  });
});

ipcMain.on('sync-titlebar-bg', (_event, colorStr) => {
  if (!mainWindow || mainWindow.isDestroyed() || !colorStr || typeof colorStr !== 'string') return;
  const safeColor = colorStr.trim();
  if (!/^#[0-9a-fA-F]{6}$/.test(safeColor) && !/^rgba?\([0-9.,\s]+\)$/.test(safeColor)) return;
  mainWindow.webContents.executeJavaScript(
    `document.documentElement.style.background=${JSON.stringify(safeColor)};document.body.style.background=${JSON.stringify(safeColor)};`,
    true
  ).catch(() => {});
});

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
