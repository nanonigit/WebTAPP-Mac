const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  buildApp: (params) => ipcRenderer.invoke('build-app', params),
  selectIconFile: () => ipcRenderer.invoke('select-icon-file'),
  selectOutputDir: () => ipcRenderer.invoke('select-output-dir'),
  showInFinder: (filePath) => ipcRenderer.invoke('show-in-finder', filePath),
  launchApp: (appPath) => ipcRenderer.invoke('launch-app', appPath),
  deleteApp: (appPath) => ipcRenderer.invoke('delete-app', appPath),
  listInstalledApps: () => ipcRenderer.invoke('list-installed-apps'),
  getRuntimeStatus: () => ipcRenderer.invoke('get-runtime-status'),
  getBuildHistory: () => ipcRenderer.invoke('get-build-history'),
  clearBuildHistory: () => ipcRenderer.invoke('clear-build-history'),
  updateApp: () => ipcRenderer.invoke('update-app'),
  onBuildLog: (callback) => {
    const listener = (_event, chunk) => callback(chunk);
    ipcRenderer.on('build-log', listener);
    return () => ipcRenderer.removeListener('build-log', listener);
  }
});
