import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

// Detect if running in Tauri
const isTauri = process.env.TAURI_PLATFORM !== undefined

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // Tauri expects a fixed port
    host: true,
    open: false,
    cors: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
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
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Tauri uses Chromium on Windows (WebView2), target accordingly
    target: isTauri ? 'chrome105' : 'esnext',
  },
  // Environment variables
  envPrefix: ['VITE_', 'TAURI_'],
  clearScreen: false,
})