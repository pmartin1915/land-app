/**
 * Mock Tauri APIs for testing
 * These mocks allow components that use Tauri to run in jsdom
 */

import { vi } from 'vitest'

// Mock @tauri-apps/api
export const invoke = vi.fn()
export const convertFileSrc = vi.fn((path: string) => `file://${path}`)

export const event = {
  listen: vi.fn(() => Promise.resolve(() => {})),
  once: vi.fn(() => Promise.resolve(() => {})),
  emit: vi.fn(() => Promise.resolve()),
}

export const window = {
  appWindow: {
    listen: vi.fn(() => Promise.resolve(() => {})),
    close: vi.fn(),
    minimize: vi.fn(),
    maximize: vi.fn(),
    setTitle: vi.fn(),
  },
  getCurrent: vi.fn(() => ({
    listen: vi.fn(() => Promise.resolve(() => {})),
    close: vi.fn(),
    minimize: vi.fn(),
    maximize: vi.fn(),
    setTitle: vi.fn(),
  })),
}

export const path = {
  appDataDir: vi.fn(() => Promise.resolve('/mock/app/data')),
  appConfigDir: vi.fn(() => Promise.resolve('/mock/app/config')),
  appCacheDir: vi.fn(() => Promise.resolve('/mock/app/cache')),
  join: vi.fn((...paths: string[]) => Promise.resolve(paths.join('/'))),
}

export const os = {
  platform: vi.fn(() => Promise.resolve('win32')),
  arch: vi.fn(() => Promise.resolve('x86_64')),
  version: vi.fn(() => Promise.resolve('10.0.0')),
}

export default {
  invoke,
  convertFileSrc,
  event,
  window,
  path,
  os,
}
