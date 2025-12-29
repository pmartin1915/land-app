import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    exclude: ['node_modules', 'dist', 'src-tauri'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/types/*',
      ],
    },
    // Mock Tauri APIs in tests
    alias: {
      '@tauri-apps/api': resolve(__dirname, 'src/test/mocks/tauri.ts'),
      '@tauri-apps/plugin-dialog': resolve(__dirname, 'src/test/mocks/tauri-plugins.ts'),
      '@tauri-apps/plugin-fs': resolve(__dirname, 'src/test/mocks/tauri-plugins.ts'),
      '@tauri-apps/plugin-os': resolve(__dirname, 'src/test/mocks/tauri-plugins.ts'),
      '@tauri-apps/plugin-process': resolve(__dirname, 'src/test/mocks/tauri-plugins.ts'),
      '@tauri-apps/plugin-shell': resolve(__dirname, 'src/test/mocks/tauri-plugins.ts'),
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      '@components': resolve(__dirname, 'src/components'),
      '@lib': resolve(__dirname, 'src/lib'),
      '@pages': resolve(__dirname, 'src/pages'),
      '@styles': resolve(__dirname, 'src/styles'),
    },
  },
})
