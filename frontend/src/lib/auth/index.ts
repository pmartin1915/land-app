/**
 * Authentication Module
 *
 * Provides web-based authentication using localStorage for token storage.
 */

export type { AuthAdapter, AuthTokens, AuthAdapterConfig } from './AuthAdapter'
export { WebAuthAdapter } from './WebAuthAdapter'

import { AuthAdapter } from './AuthAdapter'
import { WebAuthAdapter } from './WebAuthAdapter'

// Singleton instance
let authAdapterInstance: AuthAdapter | null = null

/**
 * Get the singleton auth adapter instance.
 */
export function getAuthAdapterInstance(): AuthAdapter {
  if (!authAdapterInstance) {
    authAdapterInstance = new WebAuthAdapter()
  }
  return authAdapterInstance
}

export default getAuthAdapterInstance
