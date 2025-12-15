import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron'
import { resolve } from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    electron([
      {
        // Main-Process entry file of the Electron App.
        entry: 'electron/main.ts',
      },
      {
        entry: 'electron/preload.ts',
        onstart(options) {
          // Notify the Renderer-Process to reload the page when the Preload-Scripts build is complete,
          // instead of restarting the entire Electron App.
          options.reload()
        },
      },
    ])
  ],
  server: {
    port: parseInt(process.env.VITE_DEV_PORT || '5173'),
    host: true,
    strictPort: false, // Allow Vite to try other ports if the preferred one is taken
    open: false, // Don't auto-open browser - let the launcher handle this
    cors: true,
    proxy: {
      // Proxy API calls to backend during development
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
  },
  // Required for Electron
  base: process.env.ELECTRON == 'true' ? './' : '/',
})