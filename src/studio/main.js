const { app, BrowserWindow, ipcMain, dialog, shell, Menu } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow = null;

// Resolve project root (works both inside .app and in development)
function getProjectRoot() {
  // If running inside Resources/app/, project root is passed or relative
  return path.resolve(__dirname, '../../..');
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 840,
    height: 800,
    minWidth: 600,
    minHeight: 600,
    title: "Web-to-App Studio",
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 14, y: 14 },
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
      label: 'Web-to-App Studio',
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
    title: "Select Application Icon",
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

ipcMain.handle('show-in-finder', (event, filePath) => {
  if (filePath) {
    shell.showItemInFolder(filePath);
  }
});

ipcMain.handle('build-app', async (event, params) => {
  return new Promise((resolve) => {
    const pythonScript = path.join(getProjectRoot(), 'src', 'generator', 'build_app.py');
    const args = [
      pythonScript,
      '--name', params.name,
      '--url', params.url
    ];

    if (params.icon) {
      args.push('--icon', params.icon);
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
    if (params.install) {
      args.push('--install');
    }

    const pyProc = spawn('python3', args, {
      cwd: getProjectRoot(),
      env: process.env
    });

    let output = '';
    let errorOutput = '';

    pyProc.stdout.on('data', (data) => {
      output += data.toString();
    });

    pyProc.stderr.on('data', (data) => {
      errorOutput += data.toString();
    });

    pyProc.on('close', (code) => {
      if (code === 0) {
        // Extract App Path from output
        const match = output.match(/App Path\s*:\s*(.*)/);
        const appPath = match ? match[1].trim() : (params.install ? path.join(app.getPath('home'), 'Applications', `${params.name}.app`) : path.join(getProjectRoot(), `${params.name}.app`));
        resolve({ success: true, path: appPath, log: output });
      } else {
        resolve({ success: false, error: errorOutput || output || `Process exited with code ${code}` });
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
