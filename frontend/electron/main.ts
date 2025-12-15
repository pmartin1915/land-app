import { app, BrowserWindow, shell, ipcMain, Menu, safeStorage } from 'electron'
import { release } from 'node:os'
import { join } from 'node:path'
import * as fs from 'node:fs'

// The built directory structure
//
// ├─┬ dist-electron
// │ ├─┬ main.js    > Electron-Main
// │ └─┬ preload.js > Preload-Scripts
// ├─┬ dist
// │ └── index.html  > Electron-Renderer
//
process.env.DIST_ELECTRON = join(__dirname, '..')
process.env.DIST = join(process.env.DIST_ELECTRON, '../dist')
process.env.VITE_PUBLIC = process.env.VITE_DEV_SERVER_URL
  ? join(process.env.DIST_ELECTRON, '../public')
  : process.env.DIST

// Disable GPU Acceleration for Windows 7
if (release().startsWith('6.1')) app.disableHardwareAcceleration()

// Set application name for Windows 10+ notifications
if (process.platform === 'win32') app.setAppUserModelId(app.getName())

if (!app.requestSingleInstanceLock()) {
  app.quit()
  process.exit(0)
}

// Remove electron security warnings
// This should only be used when you know what you're doing
process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = 'true'

let win: BrowserWindow | null = null
// Here, you can also use other preload
const preload = join(__dirname, '../preload.js')

// Enhanced URL detection for dynamic ports
function getServerUrl(): string {
  // Check environment variable first
  if (process.env.VITE_DEV_SERVER_URL) {
    return process.env.VITE_DEV_SERVER_URL
  }

  // Try to detect from common development ports
  const commonPorts = [5173, 5174, 5175, 3000, 3001]

  // For now, use the configured port or fallback
  const port = process.env.VITE_DEV_PORT || '5173'
  return `http://localhost:${port}`
}

const url = getServerUrl()
const indexHtml = join(process.env.DIST, 'index.html')

// Secure token storage utilities
const TokenManager = {
  // Store authentication token securely
  storeToken(token: string, refreshToken?: string): boolean {
    try {
      if (safeStorage.isEncryptionAvailable()) {
        const encryptedToken = safeStorage.encryptString(token)
        // Store in user data directory
        const userDataPath = app.getPath('userData')
        const tokenPath = join(userDataPath, 'auth_token')

        fs.writeFileSync(tokenPath, encryptedToken)

        if (refreshToken) {
          const encryptedRefreshToken = safeStorage.encryptString(refreshToken)
          fs.writeFileSync(join(userDataPath, 'refresh_token'), encryptedRefreshToken)
        }

        return true
      } else {
        console.warn('Secure storage not available, storing token in plain text')
        // Fallback to localStorage via renderer process
        return false
      }
    } catch (error) {
      console.error('Failed to store token:', error)
      return false
    }
  },

  // Retrieve authentication token securely
  getToken(): string | null {
    try {
      const userDataPath = app.getPath('userData')
      const tokenPath = join(userDataPath, 'auth_token')

      if (fs.existsSync(tokenPath) && safeStorage.isEncryptionAvailable()) {
        const encryptedToken = fs.readFileSync(tokenPath)
        return safeStorage.decryptString(encryptedToken)
      }

      return null
    } catch (error) {
      console.error('Failed to retrieve token:', error)
      return null
    }
  },

  // Clear stored tokens
  clearTokens(): void {
    try {
      const userDataPath = app.getPath('userData')
      const tokenPath = join(userDataPath, 'auth_token')
      const refreshPath = join(userDataPath, 'refresh_token')

      if (fs.existsSync(tokenPath)) {
        fs.unlinkSync(tokenPath)
      }
      if (fs.existsSync(refreshPath)) {
        fs.unlinkSync(refreshPath)
      }
    } catch (error) {
      console.error('Failed to clear tokens:', error)
    }
  }
}

async function createWindow() {
  win = new BrowserWindow({
    title: 'Alabama Auction Watcher',
    icon: join(process.env.VITE_PUBLIC, 'favicon.ico'),
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 800,
    webPreferences: {
      preload,
      // Warning: Enable nodeIntegration and disable contextIsolation is not secure in production
      nodeIntegration: true,
      contextIsolation: false,
    },
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    show: false, // Don't show until ready
  })

  // Show window when ready to prevent visual flash
  win.once('ready-to-show', () => {
    win?.show()

    // Open DevTools in development
    if (process.env.VITE_DEV_SERVER_URL) {
      win?.webContents.openDevTools()
    }
  })

  // Enhanced loading with retry logic for development server
  if (process.env.VITE_DEV_SERVER_URL || url.includes('localhost')) {
    console.log('Loading development server:', url)

    // Try to load the URL with timeout and fallback
    const loadWithTimeout = new Promise<void>((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        reject(new Error('Development server connection timeout'))
      }, 10000) // 10 second timeout

      win.loadURL(url).then(() => {
        clearTimeout(timeoutId)
        console.log('Successfully connected to development server')
        // Open devTool if the app is not packaged
        win.webContents.openDevTools()
        resolve()
      }).catch((error) => {
        clearTimeout(timeoutId)
        console.error('Failed to connect to development server:', error)
        reject(error)
      })
    })

    // Handle connection failure
    loadWithTimeout.catch((error) => {
      console.warn('Development server not available, loading built version')
      console.warn('Error:', error.message)

      // Fallback to built version
      if (fs.existsSync(indexHtml)) {
        win.loadFile(indexHtml)
      } else {
        // Show error page if nothing is available
        win.loadURL(`data:text/html,<html><body>
          <h1>Alabama Auction Watcher</h1>
          <p>Development server not available and built version not found.</p>
          <p>Please start the development server or build the application.</p>
          <p>Server URL attempted: ${url}</p>
        </body></html>`)
      }
    })

  } else {
    console.log('Loading built application')
    win.loadFile(indexHtml)
  }

  // Test actively push message to the Electron-Renderer
  win.webContents.on('did-finish-load', () => {
    win?.webContents.send('main-process-message', new Date().toLocaleString())
  })

  // Make all links open with the browser, not with the application
  win.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('https:')) shell.openExternal(url)
    return { action: 'deny' }
  })
}

// Create application menu
function createMenu() {
  const template: any[] = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Import CSV',
          accelerator: 'CmdOrCtrl+I',
          click: () => {
            win?.webContents.send('menu-import-csv')
          }
        },
        {
          label: 'Export Data',
          accelerator: 'CmdOrCtrl+E',
          click: () => {
            win?.webContents.send('menu-export-data')
          }
        },
        { type: 'separator' },
        {
          label: 'Exit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.quit()
          }
        }
      ]
    },
    {
      label: 'View',
      submenu: [
        {
          label: 'Dashboard',
          accelerator: 'CmdOrCtrl+1',
          click: () => {
            win?.webContents.send('menu-navigate', 'dashboard')
          }
        },
        {
          label: 'Parcels',
          accelerator: 'CmdOrCtrl+2',
          click: () => {
            win?.webContents.send('menu-navigate', 'parcels')
          }
        },
        {
          label: 'Map',
          accelerator: 'CmdOrCtrl+3',
          click: () => {
            win?.webContents.send('menu-navigate', 'map')
          }
        },
        {
          label: 'Triage',
          accelerator: 'CmdOrCtrl+T',
          click: () => {
            win?.webContents.send('menu-navigate', 'triage')
          }
        },
        { type: 'separator' },
        {
          label: 'Toggle Search',
          accelerator: 'CmdOrCtrl+/',
          click: () => {
            win?.webContents.send('menu-toggle-search')
          }
        },
        {
          label: 'Toggle Theme',
          accelerator: 'CmdOrCtrl+Shift+T',
          click: () => {
            win?.webContents.send('menu-toggle-theme')
          }
        }
      ]
    },
    {
      label: 'Help',
      submenu: [
        {
          label: 'Keyboard Shortcuts',
          accelerator: 'CmdOrCtrl+?',
          click: () => {
            win?.webContents.send('menu-show-shortcuts')
          }
        },
        {
          label: 'About',
          click: () => {
            win?.webContents.send('menu-show-about')
          }
        }
      ]
    }
  ]

  // macOS specific menu adjustments
  if (process.platform === 'darwin') {
    template.unshift({
      label: app.getName(),
      submenu: [
        { label: 'About ' + app.getName(), role: 'about' },
        { type: 'separator' },
        { label: 'Services', role: 'services', submenu: [] },
        { type: 'separator' },
        { label: 'Hide ' + app.getName(), accelerator: 'Command+H', role: 'hide' },
        { label: 'Hide Others', accelerator: 'Command+Shift+H', role: 'hideothers' },
        { label: 'Show All', role: 'unhide' },
        { type: 'separator' },
        { label: 'Quit', accelerator: 'Command+Q', click: () => app.quit() }
      ]
    })
  }

  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

// IPC handlers for authentication and app management
ipcMain.handle('store-auth-token', async (_, token: string, refreshToken?: string) => {
  return TokenManager.storeToken(token, refreshToken)
})

ipcMain.handle('get-auth-token', async () => {
  return TokenManager.getToken()
})

ipcMain.handle('clear-auth-tokens', async () => {
  TokenManager.clearTokens()
  return true
})

ipcMain.handle('get-server-info', async () => {
  return {
    serverUrl: url,
    isDevelopment: !!process.env.VITE_DEV_SERVER_URL,
    electronVersion: process.versions.electron,
    nodeVersion: process.versions.node
  }
})

// Enhanced window creation with better error handling
app.whenReady().then(() => {
  createWindow()
  createMenu()

  // Log startup information
  console.log('Alabama Auction Watcher starting...')
  console.log('Server URL:', url)
  console.log('Development mode:', !!process.env.VITE_DEV_SERVER_URL)
  console.log('Secure storage available:', safeStorage.isEncryptionAvailable())
})

app.on('window-all-closed', () => {
  win = null
  if (process.platform !== 'darwin') app.quit()
})

app.on('second-instance', () => {
  if (win) {
    // Focus on the main window if the user tried to open another
    if (win.isMinimized()) win.restore()
    win.focus()
  }
})

app.on('activate', () => {
  const allWindows = BrowserWindow.getAllWindows()
  if (allWindows.length) {
    allWindows[0].focus()
  } else {
    createWindow()
  }
})

// New window example arg: new windows url
ipcMain.handle('open-win', (_, arg) => {
  const childWindow = new BrowserWindow({
    webPreferences: {
      preload,
      nodeIntegration: true,
      contextIsolation: false,
    },
  })

  if (process.env.VITE_DEV_SERVER_URL) {
    childWindow.loadURL(`${url}#${arg}`)
  } else {
    childWindow.loadFile(indexHtml, { hash: arg })
  }
})