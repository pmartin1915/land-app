/**
 * Web Authentication Adapter
 *
 * Uses localStorage for token storage in browser environments.
 * Fallback adapter when Tauri is not available.
 */

import { AuthAdapter, AuthTokens, AuthAdapterConfig } from './AuthAdapter'
import { config } from '../../config'

const DEFAULT_CONFIG: Required<AuthAdapterConfig> = {
  tokenKey: config.auth.tokenKey,
  refreshTokenKey: config.auth.refreshTokenKey,
  expiresKey: config.auth.tokenExpiresKey,
  deviceIdKey: config.auth.deviceIdKey,
}

export class WebAuthAdapter implements AuthAdapter {
  private config: Required<AuthAdapterConfig>

  constructor(adapterConfig?: AuthAdapterConfig) {
    this.config = { ...DEFAULT_CONFIG, ...adapterConfig }
  }

  async storeTokens(tokens: AuthTokens): Promise<void> {
    try {
      localStorage.setItem(this.config.tokenKey, tokens.accessToken)

      if (tokens.refreshToken) {
        localStorage.setItem(this.config.refreshTokenKey, tokens.refreshToken)
      }

      if (tokens.expiresAt) {
        localStorage.setItem(this.config.expiresKey, tokens.expiresAt.toString())
      }
    } catch (error) {
      console.error('[WebAuthAdapter] Failed to store tokens:', error)
      throw new Error('Failed to store authentication tokens')
    }
  }

  async getTokens(): Promise<AuthTokens | null> {
    try {
      const accessToken = localStorage.getItem(this.config.tokenKey)
      if (!accessToken) {
        return null
      }

      const refreshToken = localStorage.getItem(this.config.refreshTokenKey) || undefined
      const expiresStr = localStorage.getItem(this.config.expiresKey)
      const expiresAt = expiresStr ? parseInt(expiresStr, 10) : undefined

      return {
        accessToken,
        refreshToken,
        expiresAt,
      }
    } catch (error) {
      console.error('[WebAuthAdapter] Failed to get tokens:', error)
      return null
    }
  }

  async clearTokens(): Promise<void> {
    try {
      localStorage.removeItem(this.config.tokenKey)
      localStorage.removeItem(this.config.refreshTokenKey)
      localStorage.removeItem(this.config.expiresKey)
    } catch (error) {
      console.error('[WebAuthAdapter] Failed to clear tokens:', error)
    }
  }

  async isExpired(): Promise<boolean> {
    try {
      const expiresStr = localStorage.getItem(this.config.expiresKey)
      if (!expiresStr) {
        return true
      }

      const expiresAt = parseInt(expiresStr, 10)
      const now = Math.floor(Date.now() / 1000)
      const bufferSeconds = 60 // Expire 1 minute early

      return now >= expiresAt - bufferSeconds
    } catch {
      return true
    }
  }

  getDeviceId(): string {
    let deviceId = localStorage.getItem(this.config.deviceIdKey)

    if (!deviceId) {
      // Generate a unique device ID based on browser characteristics
      const userAgent = navigator.userAgent
      const screen = `${window.screen.width}x${window.screen.height}`
      const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone
      const platform = navigator.platform

      const combined = `${userAgent}-${screen}-${timezone}-${platform}-${Date.now()}`
      deviceId = btoa(combined).replace(/[^a-zA-Z0-9]/g, '').substring(0, 20)

      localStorage.setItem(this.config.deviceIdKey, deviceId)
    }

    return deviceId
  }
}
