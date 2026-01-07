/**
 * Tauri Authentication Adapter
 *
 * Uses system keyring for secure token storage in desktop environments.
 * Falls back to WebAuthAdapter if Tauri is not available.
 */

import { AuthAdapter, AuthTokens, AuthAdapterConfig } from './AuthAdapter'
import { WebAuthAdapter } from './WebAuthAdapter'
import { config } from '../../config'

// Tauri invoke types
declare global {
  interface Window {
    __TAURI__?: {
      core: {
        invoke: <T>(cmd: string, args?: Record<string, unknown>) => Promise<T>
      }
    }
  }
}

interface TauriAuthError {
  code: string
  message: string
}

export class TauriAuthAdapter implements AuthAdapter {
  private webFallback: WebAuthAdapter
  private deviceId: string | null = null

  constructor(adapterConfig?: AuthAdapterConfig) {
    // Keep web adapter as fallback
    this.webFallback = new WebAuthAdapter(adapterConfig)
  }

  private get isTauriAvailable(): boolean {
    return config.isTauri && !!window.__TAURI__?.core?.invoke
  }

  private async invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
    if (!this.isTauriAvailable) {
      throw new Error('Tauri is not available')
    }
    return window.__TAURI__!.core.invoke<T>(cmd, args)
  }

  async storeTokens(tokens: AuthTokens): Promise<void> {
    if (!this.isTauriAvailable) {
      return this.webFallback.storeTokens(tokens)
    }

    try {
      await this.invoke<boolean>('store_auth_token', {
        token: tokens.accessToken,
        refreshToken: tokens.refreshToken || null,
      })

      // Store expiration in localStorage (not sensitive data)
      if (tokens.expiresAt) {
        localStorage.setItem(config.auth.tokenExpiresKey, tokens.expiresAt.toString())
      }
    } catch (error) {
      const authError = error as TauriAuthError
      console.error('[TauriAuthAdapter] Failed to store tokens:', authError.message || error)

      // Fall back to web storage on keyring failure
      console.warn('[TauriAuthAdapter] Falling back to localStorage')
      return this.webFallback.storeTokens(tokens)
    }
  }

  async getTokens(): Promise<AuthTokens | null> {
    if (!this.isTauriAvailable) {
      return this.webFallback.getTokens()
    }

    try {
      const accessToken = await this.invoke<string | null>('get_auth_token')

      if (!accessToken) {
        // Check fallback storage
        return this.webFallback.getTokens()
      }

      const expiresStr = localStorage.getItem(config.auth.tokenExpiresKey)
      const expiresAt = expiresStr ? parseInt(expiresStr, 10) : undefined

      return {
        accessToken,
        expiresAt,
      }
    } catch (error) {
      const authError = error as TauriAuthError
      console.error('[TauriAuthAdapter] Failed to get tokens:', authError.message || error)

      // Fall back to web storage
      return this.webFallback.getTokens()
    }
  }

  async clearTokens(): Promise<void> {
    // Clear both Tauri keyring and localStorage fallback
    if (this.isTauriAvailable) {
      try {
        await this.invoke<boolean>('clear_auth_tokens')
      } catch (error) {
        console.error('[TauriAuthAdapter] Failed to clear keyring tokens:', error)
      }
    }

    // Always clear localStorage too
    await this.webFallback.clearTokens()
  }

  async isExpired(): Promise<boolean> {
    // Expiration is stored in localStorage for both adapters
    return this.webFallback.isExpired()
  }

  getDeviceId(): string {
    if (this.deviceId) {
      return this.deviceId
    }

    // For Tauri, generate a stable device ID based on machine characteristics
    // Use the same logic as web for now, but could use Tauri OS info in future
    this.deviceId = this.webFallback.getDeviceId()
    return this.deviceId
  }
}
