/**
 * Authentication Module
 *
 * Provides a unified authentication interface that automatically selects
 * the appropriate adapter based on the runtime environment.
 */

export type { AuthAdapter, AuthTokens, AuthAdapterConfig } from './AuthAdapter'
export { WebAuthAdapter } from './WebAuthAdapter'
export { TauriAuthAdapter } from './TauriAuthAdapter'

import { AuthAdapter } from './AuthAdapter'
import { WebAuthAdapter } from './WebAuthAdapter'
import { TauriAuthAdapter } from './TauriAuthAdapter'
import { config } from '../../config'

/**
 * Get the appropriate auth adapter for the current environment.
 *
 * - In Tauri desktop app: Uses TauriAuthAdapter (with keyring)
 * - In browser: Uses WebAuthAdapter (with localStorage)
 */
export function getAuthAdapter(): AuthAdapter {
  if (config.isTauri) {
    return new TauriAuthAdapter()
  }
  return new WebAuthAdapter()
}

// Singleton instance for convenience
let authAdapterInstance: AuthAdapter | null = null

/**
 * Get the singleton auth adapter instance.
 * Use this for most cases to avoid creating multiple adapters.
 */
export function getAuthAdapterInstance(): AuthAdapter {
  if (!authAdapterInstance) {
    authAdapterInstance = getAuthAdapter()
  }
  return authAdapterInstance
}

// Default export for convenience
export default getAuthAdapterInstance
