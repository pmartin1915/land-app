/**
 * Desktop Bridge - Abstraction layer for desktop platform APIs
 *
 * This module provides a unified API for desktop features that works across:
 * - Tauri (primary target)
 * - Electron (legacy support)
 * - Web browser (fallback)
 *
 * IMPORTANT: Do not import Tauri/Electron APIs directly into React components.
 * Always use this bridge to enable easier testing and browser fallback.
 */

import { invoke } from '@tauri-apps/api/core'
import { listen, type UnlistenFn } from '@tauri-apps/api/event'
import { open, save, type OpenDialogOptions, type SaveDialogOptions } from '@tauri-apps/plugin-dialog'
import { readTextFile, writeTextFile } from '@tauri-apps/plugin-fs'

// Platform detection
const isTauri = typeof window !== 'undefined' && '__TAURI__' in window
const isElectron = typeof window !== 'undefined' && 'electronAPI' in window

export type Platform = 'tauri' | 'electron' | 'web'

export interface DesktopAPI {
  // Platform info
  platform: Platform
  isTauri: boolean
  isElectron: boolean
  isWeb: boolean

  // Menu event listeners
  onMenuImportCSV: (callback: () => void) => Promise<UnlistenFn | (() => void)>
  onMenuExportData: (callback: () => void) => Promise<UnlistenFn | (() => void)>
  onMenuNavigate: (callback: (route: string) => void) => Promise<UnlistenFn | (() => void)>
  onMenuToggleSearch: (callback: () => void) => Promise<UnlistenFn | (() => void)>
  onMenuToggleTheme: (callback: () => void) => Promise<UnlistenFn | (() => void)>
  onMenuShowShortcuts: (callback: () => void) => Promise<UnlistenFn | (() => void)>
  onMenuShowAbout: (callback: () => void) => Promise<UnlistenFn | (() => void)>

  // File system operations
  showSaveDialog: (options?: SaveDialogOptions) => Promise<string | null>
  showOpenDialog: (options?: OpenDialogOptions) => Promise<string[] | null>
  writeFile: (path: string, data: string) => Promise<void>
  readFile: (path: string) => Promise<string>

  // Auth token management (secure storage)
  storeAuthToken: (token: string, refreshToken?: string) => Promise<boolean>
  getAuthToken: () => Promise<string | null>
  clearAuthTokens: () => Promise<boolean>

  // Server info
  getServerInfo: () => Promise<{
    serverUrl: string
    isDevelopment: boolean
    tauriVersion?: string
    electronVersion?: string
  }>
}

// Tauri implementation
function createTauriAPI(): DesktopAPI {
  return {
    platform: 'tauri',
    isTauri: true,
    isElectron: false,
    isWeb: false,

    onMenuImportCSV: (callback) => listen('menu-import-csv', callback),
    onMenuExportData: (callback) => listen('menu-export-data', callback),
    onMenuNavigate: (callback) => listen<string>('menu-navigate', (event) => callback(event.payload)),
    onMenuToggleSearch: (callback) => listen('menu-toggle-search', callback),
    onMenuToggleTheme: (callback) => listen('menu-toggle-theme', callback),
    onMenuShowShortcuts: (callback) => listen('menu-show-shortcuts', callback),
    onMenuShowAbout: (callback) => listen('menu-show-about', callback),

    showSaveDialog: async (options) => {
      const path = await save({
        filters: options?.filters || [
          { name: 'CSV', extensions: ['csv'] },
          { name: 'JSON', extensions: ['json'] }
        ],
        ...options
      })
      return path
    },

    showOpenDialog: async (options) => {
      const result = await open({
        multiple: options?.multiple ?? true,
        filters: options?.filters || [{ name: 'CSV', extensions: ['csv'] }],
        ...options
      })
      if (Array.isArray(result)) return result
      if (result) return [result]
      return null
    },

    writeFile: async (path, data) => {
      await writeTextFile(path, data)
    },

    readFile: async (path) => {
      return await readTextFile(path)
    },

    storeAuthToken: async (token, refreshToken) => {
      return await invoke<boolean>('store_auth_token', { token, refreshToken })
    },

    getAuthToken: async () => {
      return await invoke<string | null>('get_auth_token')
    },

    clearAuthTokens: async () => {
      return await invoke<boolean>('clear_auth_tokens')
    },

    getServerInfo: async () => {
      const info = await invoke<{
        server_url: string
        is_development: boolean
        tauri_version: string
      }>('get_server_info')
      return {
        serverUrl: info.server_url,
        isDevelopment: info.is_development,
        tauriVersion: info.tauri_version
      }
    }
  }
}

// Type for the electronAPI exposed via preload
interface ElectronAPI {
  onMenuImportCSV?: (callback: () => void) => void
  onMenuExportData?: (callback: () => void) => void
  onMenuNavigate?: (callback: (route: string) => void) => void
  onMenuToggleSearch?: (callback: () => void) => void
  onMenuToggleTheme?: (callback: () => void) => void
  onMenuShowShortcuts?: (callback: () => void) => void
  onMenuShowAbout?: (callback: () => void) => void
  showSaveDialog?: () => Promise<string | null>
  showOpenDialog?: () => Promise<string[] | null>
  writeFile?: (path: string, data: string) => Promise<void>
  readFile?: (path: string) => Promise<string>
}

// Type for ipcRenderer
interface IpcRenderer {
  invoke: (channel: string, ...args: unknown[]) => Promise<unknown>
}

// Extended window type for Electron
interface WindowWithElectron extends Window {
  electronAPI?: ElectronAPI
  ipcRenderer?: IpcRenderer
}

// Electron implementation (legacy support)
function createElectronAPI(): DesktopAPI {
  const api = (window as WindowWithElectron).electronAPI

  const noop = () => Promise.resolve(() => {})

  return {
    platform: 'electron',
    isTauri: false,
    isElectron: true,
    isWeb: false,

    onMenuImportCSV: api?.onMenuImportCSV
      ? (callback: () => void) => { api.onMenuImportCSV(callback); return Promise.resolve(() => {}) }
      : noop,
    onMenuExportData: api?.onMenuExportData
      ? (callback: () => void) => { api.onMenuExportData(callback); return Promise.resolve(() => {}) }
      : noop,
    onMenuNavigate: api?.onMenuNavigate
      ? (callback: (route: string) => void) => { api.onMenuNavigate(callback); return Promise.resolve(() => {}) }
      : noop,
    onMenuToggleSearch: api?.onMenuToggleSearch
      ? (callback: () => void) => { api.onMenuToggleSearch(callback); return Promise.resolve(() => {}) }
      : noop,
    onMenuToggleTheme: api?.onMenuToggleTheme
      ? (callback: () => void) => { api.onMenuToggleTheme(callback); return Promise.resolve(() => {}) }
      : noop,
    onMenuShowShortcuts: api?.onMenuShowShortcuts
      ? (callback: () => void) => { api.onMenuShowShortcuts(callback); return Promise.resolve(() => {}) }
      : noop,
    onMenuShowAbout: api?.onMenuShowAbout
      ? (callback: () => void) => { api.onMenuShowAbout(callback); return Promise.resolve(() => {}) }
      : noop,

    showSaveDialog: async () => {
      return api?.showSaveDialog?.() ?? null
    },

    showOpenDialog: async () => {
      return api?.showOpenDialog?.() ?? null
    },

    writeFile: async (path, data) => {
      await api?.writeFile?.(path, data)
    },

    readFile: async (path) => {
      return await api?.readFile?.(path) ?? ''
    },

    storeAuthToken: async (token, refreshToken) => {
      return await (window as WindowWithElectron).ipcRenderer?.invoke('store-auth-token', token, refreshToken) as boolean ?? false
    },

    getAuthToken: async () => {
      return await (window as WindowWithElectron).ipcRenderer?.invoke('get-auth-token') as string | null ?? null
    },

    clearAuthTokens: async () => {
      return await (window as WindowWithElectron).ipcRenderer?.invoke('clear-auth-tokens') as boolean ?? false
    },

    getServerInfo: async () => {
      const info = await (window as WindowWithElectron).ipcRenderer?.invoke('get-server-info') as { serverUrl?: string; isDevelopment?: boolean; electronVersion?: string } | undefined
      return {
        serverUrl: info?.serverUrl ?? 'http://localhost:8001',
        isDevelopment: info?.isDevelopment ?? true,
        electronVersion: info?.electronVersion
      }
    }
  }
}

// Web fallback implementation
function createWebAPI(): DesktopAPI {
  const noop = () => Promise.resolve(() => {})

  return {
    platform: 'web',
    isTauri: false,
    isElectron: false,
    isWeb: true,

    onMenuImportCSV: noop,
    onMenuExportData: noop,
    onMenuNavigate: noop,
    onMenuToggleSearch: noop,
    onMenuToggleTheme: noop,
    onMenuShowShortcuts: noop,
    onMenuShowAbout: noop,

    showSaveDialog: async () => {
      console.warn('File dialogs not available in web mode')
      return null
    },

    showOpenDialog: async () => {
      console.warn('File dialogs not available in web mode')
      return null
    },

    writeFile: async () => {
      throw new Error('File system not available in web mode')
    },

    readFile: async () => {
      throw new Error('File system not available in web mode')
    },

    storeAuthToken: async (token, refreshToken) => {
      try {
        localStorage.setItem('auth_token', token)
        if (refreshToken) {
          localStorage.setItem('refresh_token', refreshToken)
        }
        return true
      } catch {
        return false
      }
    },

    getAuthToken: async () => {
      return localStorage.getItem('auth_token')
    },

    clearAuthTokens: async () => {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('refresh_token')
      return true
    },

    getServerInfo: async () => ({
      serverUrl: import.meta.env.VITE_API_URL || 'http://localhost:8001',
      isDevelopment: import.meta.env.DEV
    })
  }
}

// Create the appropriate API based on detected platform
export const desktopAPI: DesktopAPI = isTauri
  ? createTauriAPI()
  : isElectron
    ? createElectronAPI()
    : createWebAPI()

// Extended window type for desktop API debugging
interface WindowWithDesktopAPI extends Window {
  desktopAPI?: DesktopAPI
}

// Attach to window for debugging
if (typeof window !== 'undefined') {
  (window as WindowWithDesktopAPI).desktopAPI = desktopAPI
}

// Export platform detection helpers
export { isTauri, isElectron }
export const isWeb = !isTauri && !isElectron
