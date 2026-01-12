// Electron API type definitions
export interface ElectronAPI {
  // Menu actions
  onMenuImportCSV: (callback: () => void) => void
  onMenuExportData: (callback: () => void) => void
  onMenuNavigate: (callback: (route: string) => void) => void
  onMenuToggleSearch: (callback: () => void) => void
  onMenuToggleTheme: (callback: () => void) => void
  onMenuShowShortcuts: (callback: () => void) => void
  onMenuShowAbout: (callback: () => void) => void

  // File system operations
  showSaveDialog: () => Promise<string | undefined>
  showOpenDialog: () => Promise<string[] | undefined>
  writeFile: (path: string, data: string) => Promise<void>
  readFile: (path: string) => Promise<string>

  // Platform detection
  platform: string

  // Version info
  versions: NodeJS.ProcessVersions
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
    ipcRenderer?: {
      on: (channel: string, listener: (...args: unknown[]) => void) => void
      off: (channel: string, listener: (...args: unknown[]) => void) => void
      send: (channel: string, ...args: unknown[]) => void
      invoke: (channel: string, ...args: unknown[]) => Promise<unknown>
    }
  }
}