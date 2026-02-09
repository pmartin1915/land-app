/**
 * Centralized configuration for Auction Watcher Frontend.
 * Reads from Vite environment variables at build time.
 */

const isDevelopment = import.meta.env.DEV
const isProduction = import.meta.env.PROD

// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'
const API_VERSION = 'v1'

export const config = {
  // Environment
  isDevelopment,
  isProduction,

  // API
  api: {
    baseUrl: API_BASE_URL,
    fullUrl: `${API_BASE_URL}/api/${API_VERSION}`,
    timeout: 30000,
  },

  // Auth
  auth: {
    tokenKey: 'auth_token',
    refreshTokenKey: 'refresh_token',
    tokenExpiresKey: 'token_expires',
  },

  // Features
  features: {
    enableDevTools: isDevelopment,
    enableMockData: import.meta.env.VITE_ENABLE_MOCKS === 'true',
    enableOfflineMode: import.meta.env.VITE_ENABLE_OFFLINE === 'true',
  },

  // Mapping (Mapbox)
  map: {
    accessToken: import.meta.env.VITE_MAPBOX_TOKEN || '',
    style: 'mapbox://styles/mapbox/outdoors-v12',
    defaultCenter: [-86.9023, 32.3182] as [number, number],
    defaultZoom: 7,
  },

  // App
  app: {
    name: 'Auction Watcher',
    version: '1.0.0',
  },
} as const

export type AppConfig = typeof config

if (isDevelopment) {
  console.log('[Config] Loaded configuration:', {
    environment: 'development',
    apiUrl: config.api.fullUrl,
  })
}
