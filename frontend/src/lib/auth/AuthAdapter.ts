/**
 * Authentication Adapter Interface
 *
 * Provides a unified interface for authentication storage.
 * Implementation: WebAuthAdapter (uses localStorage)
 */

export interface AuthTokens {
  accessToken: string
  refreshToken?: string
  expiresAt?: number // Unix timestamp in seconds
}

export interface AuthAdapter {
  storeTokens(tokens: AuthTokens): Promise<void>
  getTokens(): Promise<AuthTokens | null>
  clearTokens(): Promise<void>
  isExpired(): Promise<boolean>
}

export interface AuthAdapterConfig {
  tokenKey?: string
  refreshTokenKey?: string
  expiresKey?: string
}
