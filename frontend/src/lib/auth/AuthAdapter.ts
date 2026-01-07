/**
 * Authentication Adapter Interface
 *
 * Provides a unified interface for authentication storage across different platforms.
 * Implementations:
 * - WebAuthAdapter: Uses localStorage (browser)
 * - TauriAuthAdapter: Uses system keyring (desktop app)
 */

export interface AuthTokens {
  accessToken: string
  refreshToken?: string
  expiresAt?: number // Unix timestamp in seconds
}

export interface AuthAdapter {
  /**
   * Store authentication tokens
   */
  storeTokens(tokens: AuthTokens): Promise<void>

  /**
   * Retrieve stored tokens
   */
  getTokens(): Promise<AuthTokens | null>

  /**
   * Clear all stored tokens
   */
  clearTokens(): Promise<void>

  /**
   * Check if tokens are expired
   */
  isExpired(): Promise<boolean>

  /**
   * Get device ID for this client
   */
  getDeviceId(): string
}

export interface AuthAdapterConfig {
  tokenKey?: string
  refreshTokenKey?: string
  expiresKey?: string
  deviceIdKey?: string
}
