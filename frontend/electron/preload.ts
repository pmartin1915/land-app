import { contextBridge, ipcRenderer } from 'electron'

// --------- Expose some API to the Renderer process ---------
contextBridge.exposeInMainWorld('ipcRenderer', {
  on: ipcRenderer.on.bind(ipcRenderer),
  off: ipcRenderer.removeListener.bind(ipcRenderer),
  send: ipcRenderer.send.bind(ipcRenderer),
  invoke: ipcRenderer.invoke.bind(ipcRenderer),
})

// Expose Electron APIs for the application
contextBridge.exposeInMainWorld('electronAPI', {
  // Menu actions
  onMenuImportCSV: (callback: () => void) => {
    ipcRenderer.on('menu-import-csv', callback)
  },
  onMenuExportData: (callback: () => void) => {
    ipcRenderer.on('menu-export-data', callback)
  },
  onMenuNavigate: (callback: (route: string) => void) => {
    ipcRenderer.on('menu-navigate', (_, route) => callback(route))
  },
  onMenuToggleSearch: (callback: () => void) => {
    ipcRenderer.on('menu-toggle-search', callback)
  },
  onMenuToggleTheme: (callback: () => void) => {
    ipcRenderer.on('menu-toggle-theme', callback)
  },
  onMenuShowShortcuts: (callback: () => void) => {
    ipcRenderer.on('menu-show-shortcuts', callback)
  },
  onMenuShowAbout: (callback: () => void) => {
    ipcRenderer.on('menu-show-about', callback)
  },

  // File system operations
  showSaveDialog: () => ipcRenderer.invoke('show-save-dialog'),
  showOpenDialog: () => ipcRenderer.invoke('show-open-dialog'),
  writeFile: (path: string, data: string) => ipcRenderer.invoke('write-file', path, data),
  readFile: (path: string) => ipcRenderer.invoke('read-file', path),

  // Platform detection
  platform: process.platform,

  // Version info
  versions: process.versions,
})