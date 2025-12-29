/**
 * Centralized configuration for Alabama Auction Watcher Frontend.
 * Reads from Vite environment variables at build time.
 */

// Detect environment
const isTauri = '__TAURI__' in window
const isDevelopment = import.meta.env.DEV
const isProduction = import.meta.env.PROD

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'
const API_VERSION = 'v1'

export const config = {
  // Environment
  isDevelopment,
  isProduction,
  isTauri,

  // API
  api: {
    baseUrl: API_BASE_URL,
    fullUrl: `${API_BASE_URL}/api/${API_VERSION}`,
    timeout: 30000, // 30 seconds
  },

  // Auth
  auth: {
    tokenKey: 'auth_token',
    refreshTokenKey: 'refresh_token',
    tokenExpiresKey: 'token_expires',
    deviceIdKey: 'device_id',
  },

  // Features
  features: {
    // Enable/disable features based on environment
    enableDevTools: isDevelopment,
    enableMockData: import.meta.env.VITE_ENABLE_MOCKS === 'true',
    enableOfflineMode: import.meta.env.VITE_ENABLE_OFFLINE === 'true',
  },

  // Mapping (Mapbox)
  map: {
    accessToken: import.meta.env.VITE_MAPBOX_TOKEN || '',
    style: 'mapbox://styles/mapbox/outdoors-v12',
    defaultCenter: [-86.9023, 32.3182] as [number, number], // Alabama center
    defaultZoom: 7,
  },

  // App
  app: {
    name: 'Alabama Auction Watcher',
    version: '1.0.0',
  },
} as const

// Type for config
export type AppConfig = typeof config

// Debug logging in development
if (isDevelopment) {
  console.log('[Config] Loaded configuration:', {
    environment: isDevelopment ? 'development' : 'production',
    isTauri,
    apiUrl: config.api.fullUrl,
  })
}
