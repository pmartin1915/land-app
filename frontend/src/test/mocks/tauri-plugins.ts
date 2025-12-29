/**
 * Mock Tauri plugins for testing
 */

import { vi } from 'vitest'

// Mock @tauri-apps/plugin-dialog
export const open = vi.fn(() => Promise.resolve(null))
export const save = vi.fn(() => Promise.resolve(null))
export const message = vi.fn(() => Promise.resolve())
export const ask = vi.fn(() => Promise.resolve(true))
export const confirm = vi.fn(() => Promise.resolve(true))

// Mock @tauri-apps/plugin-fs
export const readTextFile = vi.fn(() => Promise.resolve(''))
export const writeTextFile = vi.fn(() => Promise.resolve())
export const readBinaryFile = vi.fn(() => Promise.resolve(new Uint8Array()))
export const writeBinaryFile = vi.fn(() => Promise.resolve())
export const readDir = vi.fn(() => Promise.resolve([]))
export const createDir = vi.fn(() => Promise.resolve())
export const removeDir = vi.fn(() => Promise.resolve())
export const removeFile = vi.fn(() => Promise.resolve())
export const renameFile = vi.fn(() => Promise.resolve())
export const copyFile = vi.fn(() => Promise.resolve())
export const exists = vi.fn(() => Promise.resolve(false))

// Mock @tauri-apps/plugin-os
export const platform = vi.fn(() => Promise.resolve('win32'))
export const arch = vi.fn(() => Promise.resolve('x86_64'))
export const version = vi.fn(() => Promise.resolve('10.0.0'))
export const type = vi.fn(() => Promise.resolve('Windows_NT'))
export const locale = vi.fn(() => Promise.resolve('en-US'))

// Mock @tauri-apps/plugin-process
export const exit = vi.fn(() => Promise.resolve())
export const relaunch = vi.fn(() => Promise.resolve())

// Mock @tauri-apps/plugin-shell
export const Command = {
  create: vi.fn(() => ({
    execute: vi.fn(() => Promise.resolve({ code: 0, stdout: '', stderr: '' })),
    spawn: vi.fn(() => Promise.resolve({ pid: 1234 })),
  })),
}
export const Child = vi.fn()
