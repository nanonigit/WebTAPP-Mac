const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  buildApp: (params) => ipcRenderer.invoke('build-app', params),
  selectIconFile: () => ipcRenderer.invoke('select-icon-file'),
  showInFinder: (filePath) => ipcRenderer.invoke('show-in-finder', filePath)
});
