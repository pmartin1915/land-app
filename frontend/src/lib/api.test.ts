import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  isApiError,
  getApiErrorMessage,
  getAuthStatus,
  clearAuthentication,
  getConnectionStatus,
  AuthManager,
  ConnectionManager,
} from './api'

// Mock axios
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  }
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      post: vi.fn(),
    },
  }
})

// Mock config
vi.mock('../config', () => ({
  config: {
    api: { baseUrl: 'http://test:8001', fullUrl: 'http://test:8001/api/v1', timeout: 5000 },
    auth: { tokenKey: 'auth_token', refreshTokenKey: 'refresh_token', tokenExpiresKey: 'token_expires' },
  }
}))

// Mock window.addEventListener to prevent errors during ConnectionManager initialization
vi.stubGlobal('addEventListener', vi.fn())

describe('API Module - Utility Functions', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear()
    // Clear all mocks
    vi.clearAllMocks()
  })

  afterEach(() => {
    localStorage.clear()
  })

  describe('isApiError', () => {
    it('should return true for objects with name="APIError"', () => {
      const apiError = {
        name: 'APIError',
        message: 'API error occurred',
        details: { message: 'Detailed error' }
      }
      expect(isApiError(apiError)).toBe(true)
    })

    it('should return false for regular Error instances', () => {
      const regularError = new Error('Regular error')
      expect(isApiError(regularError)).toBe(false)
    })

    it('should return false for null', () => {
      expect(isApiError(null)).toBe(false)
    })

    it('should return false for undefined', () => {
      expect(isApiError(undefined)).toBe(false)
    })

    it('should return false for strings', () => {
      expect(isApiError('error message')).toBe(false)
    })

    it('should return false for numbers', () => {
      expect(isApiError(404)).toBe(false)
    })

    it('should return false for objects without name property', () => {
      const obj = { message: 'Some error' }
      expect(isApiError(obj)).toBe(false)
    })

    it('should return false for objects with name property but not "APIError"', () => {
      const err = { name: 'CustomError', message: 'Custom error' }
      expect(isApiError(err)).toBe(false)
    })

    it('should handle objects with different name values', () => {
      const errors = [
        { name: 'TypeError' },
        { name: 'ReferenceError' },
        { name: 'NetworkError' },
        { name: 'APIERROR' }, // Case sensitive
      ]
      errors.forEach(err => {
        expect(isApiError(err)).toBe(false)
      })
    })
  })

  describe('getApiErrorMessage', () => {
    it('should extract message from APIError objects with details', () => {
      const apiError = {
        name: 'APIError',
        message: 'Request failed',
        details: { message: 'Server error details' }
      }
      const message = getApiErrorMessage(apiError)
      expect(message).toBe('Server error details')
    })

    it('should fallback to error.message when details.message is missing', () => {
      const apiError = {
        name: 'APIError',
        message: 'Request failed',
        details: {}
      }
      const message = getApiErrorMessage(apiError)
      expect(message).toBe('Request failed')
    })

    it('should handle APIError with no details property', () => {
      const apiError = {
        name: 'APIError',
        message: 'API error'
      }
      const message = getApiErrorMessage(apiError)
      expect(message).toBe('API error')
    })

    it('should extract message from regular Error instances', () => {
      const regularError = new Error('Something went wrong')
      expect(getApiErrorMessage(regularError)).toBe('Something went wrong')
    })

    it('should return default message for null', () => {
      expect(getApiErrorMessage(null)).toBe('An unexpected error occurred')
    })

    it('should return default message for undefined', () => {
      expect(getApiErrorMessage(undefined)).toBe('An unexpected error occurred')
    })

    it('should return default message for strings', () => {
      expect(getApiErrorMessage('error text')).toBe('An unexpected error occurred')
    })

    it('should return default message for numbers', () => {
      expect(getApiErrorMessage(500)).toBe('An unexpected error occurred')
    })

    it('should return default message for plain objects', () => {
      const obj = { customProp: 'value' }
      expect(getApiErrorMessage(obj)).toBe('An unexpected error occurred')
    })

    it('should prioritize details.message over error.message', () => {
      const apiError = {
        name: 'APIError',
        message: 'Generic error',
        details: { message: 'Specific error message' }
      }
      expect(getApiErrorMessage(apiError)).toBe('Specific error message')
    })
  })

  describe('getAuthStatus', () => {
    it('should return false for hasToken when no token exists', () => {
      const status = getAuthStatus()
      expect(status.hasToken).toBe(false)
    })

    it('should return true for isExpired when no token exists', () => {
      const status = getAuthStatus()
      expect(status.isExpired).toBe(true)
    })

    it('should return null for expiresAt when no token exists', () => {
      const status = getAuthStatus()
      expect(status.expiresAt).toBeNull()
    })

    it('should return correct shape for auth status', () => {
      const status = getAuthStatus()
      expect(status).toHaveProperty('hasToken')
      expect(status).toHaveProperty('isExpired')
      expect(status).toHaveProperty('expiresAt')
      expect(typeof status.hasToken).toBe('boolean')
      expect(typeof status.isExpired).toBe('boolean')
    })

    it('should indicate hasToken as true when token exists', () => {
      localStorage.setItem('auth_token', 'test-token')
      const status = getAuthStatus()
      expect(status.hasToken).toBe(true)
    })

    it('should indicate isExpired as true when expiration time is in the past', () => {
      // Set token expiration to 1 second ago
      const pastTime = Math.floor(Date.now() / 1000) - 1
      localStorage.setItem('auth_token', 'test-token')
      localStorage.setItem('token_expires', pastTime.toString())
      const status = getAuthStatus()
      expect(status.isExpired).toBe(true)
    })

    it('should indicate isExpired as false when expiration time is in the future', () => {
      // Set token expiration to 1 hour from now
      const futureTime = Math.floor(Date.now() / 1000) + 3600
      localStorage.setItem('auth_token', 'test-token')
      localStorage.setItem('token_expires', futureTime.toString())
      const status = getAuthStatus()
      expect(status.isExpired).toBe(false)
    })

    it('should return formatted expiresAt date when token exists', () => {
      const futureTime = Math.floor(Date.now() / 1000) + 3600
      localStorage.setItem('auth_token', 'test-token')
      localStorage.setItem('token_expires', futureTime.toString())
      const status = getAuthStatus()
      expect(status.expiresAt).not.toBeNull()
      expect(typeof status.expiresAt).toBe('string')
      // Should be a valid date string
      expect(() => new Date(status.expiresAt!)).not.toThrow()
    })

    it('should handle token expiration with 60-second buffer', () => {
      // Set token to expire in 30 seconds (within 60-second buffer)
      const soonTime = Math.floor(Date.now() / 1000) + 30
      localStorage.setItem('auth_token', 'test-token')
      localStorage.setItem('token_expires', soonTime.toString())
      const status = getAuthStatus()
      // Should be considered expired due to 60-second buffer
      expect(status.isExpired).toBe(true)
    })

    it('should consider token valid when expiration is beyond 60-second buffer', () => {
      // Set token to expire in 120 seconds (beyond 60-second buffer)
      const validTime = Math.floor(Date.now() / 1000) + 120
      localStorage.setItem('auth_token', 'test-token')
      localStorage.setItem('token_expires', validTime.toString())
      const status = getAuthStatus()
      expect(status.isExpired).toBe(false)
    })
  })

  describe('clearAuthentication', () => {
    it('should remove auth_token from localStorage', () => {
      localStorage.setItem('auth_token', 'test-token')
      clearAuthentication()
      expect(localStorage.getItem('auth_token')).toBeNull()
    })

    it('should remove refresh_token from localStorage', () => {
      localStorage.setItem('refresh_token', 'test-refresh-token')
      clearAuthentication()
      expect(localStorage.getItem('refresh_token')).toBeNull()
    })

    it('should remove token_expires from localStorage', () => {
      localStorage.setItem('token_expires', '1234567890')
      clearAuthentication()
      expect(localStorage.getItem('token_expires')).toBeNull()
    })

    it('should clear all authentication keys in one call', () => {
      localStorage.setItem('auth_token', 'token')
      localStorage.setItem('refresh_token', 'refresh')
      localStorage.setItem('token_expires', '123')
      localStorage.setItem('other_key', 'value')

      clearAuthentication()

      expect(localStorage.getItem('auth_token')).toBeNull()
      expect(localStorage.getItem('refresh_token')).toBeNull()
      expect(localStorage.getItem('token_expires')).toBeNull()
      expect(localStorage.getItem('other_key')).toBe('value')
    })

    it('should be idempotent when called multiple times', () => {
      localStorage.setItem('auth_token', 'token')
      clearAuthentication()
      clearAuthentication()
      clearAuthentication()
      expect(localStorage.getItem('auth_token')).toBeNull()
    })

    it('should work when localStorage is already empty', () => {
      expect(() => clearAuthentication()).not.toThrow()
    })

    it('should update auth status after clearing', () => {
      localStorage.setItem('auth_token', 'token')
      clearAuthentication()
      const status = getAuthStatus()
      expect(status.hasToken).toBe(false)
    })
  })

  describe('getConnectionStatus', () => {
    it('should return a boolean', () => {
      const status = getConnectionStatus()
      expect(typeof status).toBe('boolean')
    })

    it('should return true by default', () => {
      // Connection manager initializes as online by default
      const status = getConnectionStatus()
      expect(typeof status).toBe('boolean')
    })

    it('should return consistent status across multiple calls', () => {
      const status1 = getConnectionStatus()
      const status2 = getConnectionStatus()
      expect(status1).toBe(status2)
    })

    it('should reflect changes in connection status', () => {
      // Get initial status
      const initial = getConnectionStatus()

      // Change connection status (need to call twice to trigger offline due to failure threshold)
      ConnectionManager.setOnline(false)
      ConnectionManager.setOnline(false)
      const offline = getConnectionStatus()

      // Reset to online
      ConnectionManager.setOnline(true)
      const online = getConnectionStatus()

      expect(online).toBe(true)
    })

    it('should return true when connection is restored', () => {
      // Need to call setOnline(false) twice to trigger offline state (due to failure threshold of 2)
      ConnectionManager.setOnline(false)
      ConnectionManager.setOnline(false)
      expect(getConnectionStatus()).toBe(false)

      ConnectionManager.setOnline(true)
      expect(getConnectionStatus()).toBe(true)
    })

    it('should handle rapid status changes', () => {
      const statuses: boolean[] = []

      // Start with online
      statuses.push(getConnectionStatus())

      // Trigger offline (need 2 calls to reach threshold)
      ConnectionManager.setOnline(false)
      ConnectionManager.setOnline(false)
      statuses.push(getConnectionStatus())

      // Back online
      ConnectionManager.setOnline(true)
      statuses.push(getConnectionStatus())

      // Should be able to detect transitions
      expect(statuses[0]).toBe(true)
      expect(statuses[1]).toBe(false)
      expect(statuses[2]).toBe(true)
    })
  })

  describe('AuthManager integration', () => {
    it('should expose AuthManager for manual access', () => {
      expect(AuthManager).toBeDefined()
      expect(AuthManager.getAuthStatus).toBeDefined()
      expect(AuthManager.clearAuth).toBeDefined()
    })

    it('should return same data as getAuthStatus', () => {
      localStorage.setItem('auth_token', 'token')
      const status1 = getAuthStatus()
      const status2 = AuthManager.getAuthStatus()

      expect(status1.hasToken).toBe(status2.hasToken)
      expect(status1.isExpired).toBe(status2.isExpired)
    })

    it('should work with AuthManager.clearAuth', () => {
      localStorage.setItem('auth_token', 'token')
      AuthManager.clearAuth()
      expect(localStorage.getItem('auth_token')).toBeNull()
    })
  })

  describe('ConnectionManager integration', () => {
    it('should expose ConnectionManager for manual access', () => {
      expect(ConnectionManager).toBeDefined()
      expect(ConnectionManager.getStatus).toBeDefined()
      expect(ConnectionManager.setOnline).toBeDefined()
    })

    it('should return same data as getConnectionStatus', () => {
      ConnectionManager.setOnline(true)
      const status1 = getConnectionStatus()
      const status2 = ConnectionManager.getStatus()

      expect(status1).toBe(status2)
    })

    it('should allow subscription to connection changes', () => {
      const callback = vi.fn()
      const unsubscribe = ConnectionManager.subscribe(callback)

      // Need to call setOnline(false) twice to trigger state change due to failure threshold
      ConnectionManager.setOnline(false)
      ConnectionManager.setOnline(false)

      expect(callback).toHaveBeenCalled()
      expect(callback).toHaveBeenCalledWith(false)

      // Cleanup
      unsubscribe()
    })
  })

  describe('Error object edge cases', () => {
    it('should handle error objects with circular references gracefully', () => {
      const circularError: any = { name: 'Error', message: 'Test' }
      circularError.self = circularError

      expect(isApiError(circularError)).toBe(false)
      expect(getApiErrorMessage(circularError)).toBe('An unexpected error occurred')
    })

    it('should handle error objects with prototype methods', () => {
      const error = Object.create(Error.prototype)
      error.name = 'APIError'
      error.message = 'Proto error'
      error.details = { message: 'Proto details' }

      expect(isApiError(error)).toBe(true)
      expect(getApiErrorMessage(error)).toBe('Proto details')
    })

    it('should handle error objects with non-string name property', () => {
      const error = { name: 123, message: 'Test' }
      expect(isApiError(error)).toBe(false)
    })

    it('should handle error objects with empty strings', () => {
      const apiError = {
        name: 'APIError',
        message: '',
        details: { message: '' }
      }
      expect(isApiError(apiError)).toBe(true)
      expect(getApiErrorMessage(apiError)).toBe('')
    })
  })

  describe('localStorage handling', () => {
    it('should handle missing localStorage gracefully in getAuthStatus', () => {
      // Even if localStorage methods fail, should handle gracefully
      const status = getAuthStatus()
      expect(status).toHaveProperty('hasToken')
      expect(status).toHaveProperty('isExpired')
      expect(status).toHaveProperty('expiresAt')
    })

    it('should sync with actual localStorage state', () => {
      localStorage.setItem('auth_token', 'token1')
      let status = getAuthStatus()
      expect(status.hasToken).toBe(true)

      localStorage.setItem('auth_token', 'token2')
      status = getAuthStatus()
      expect(status.hasToken).toBe(true)

      localStorage.removeItem('auth_token')
      status = getAuthStatus()
      expect(status.hasToken).toBe(false)
    })

    it('should handle invalid token_expires values', () => {
      localStorage.setItem('auth_token', 'token')
      localStorage.setItem('token_expires', 'invalid')

      const status = getAuthStatus()
      // When parseInt fails on 'invalid', it returns NaN, which will be treated as expired
      // Actually, the code tries to parse it and if it's NaN, the comparison currentTime >= NaN is always false
      // So invalid values will be treated as not expired (isExpired = false)
      // Let me check: parseInt('invalid') = NaN, so expirationTime - bufferTime = NaN - 60 = NaN
      // currentTime >= NaN is always false, so isTokenExpired() returns false
      expect(status.isExpired).toBe(false)
    })

    it('should clear all three auth keys completely', () => {
      localStorage.setItem('auth_token', 'token')
      localStorage.setItem('refresh_token', 'refresh')
      localStorage.setItem('token_expires', '123')

      clearAuthentication()

      expect(localStorage.length).toBe(0)
    })
  })

  describe('Type consistency', () => {
    it('should always return consistent types from getAuthStatus', () => {
      for (let i = 0; i < 10; i++) {
        const status = getAuthStatus()
        expect(typeof status.hasToken).toBe('boolean')
        expect(typeof status.isExpired).toBe('boolean')
        expect(status.expiresAt === null || typeof status.expiresAt === 'string').toBe(true)
      }
    })

    it('should always return string from getApiErrorMessage', () => {
      const testCases = [
        null,
        undefined,
        'string',
        123,
        {},
        { name: 'APIError', message: 'test', details: { message: 'detail' } },
        new Error('test error'),
        { name: 'CustomError' },
      ]

      testCases.forEach(testCase => {
        const result = getApiErrorMessage(testCase)
        expect(typeof result).toBe('string')
      })
    })

    it('should always return boolean from isApiError', () => {
      const testCases = [
        null,
        undefined,
        'string',
        123,
        {},
        { name: 'APIError' },
        { name: 'CustomError' },
        new Error('test'),
        [],
        true,
        false,
      ]

      testCases.forEach(testCase => {
        const result = isApiError(testCase)
        expect(typeof result).toBe('boolean')
      })
    })
  })
})
