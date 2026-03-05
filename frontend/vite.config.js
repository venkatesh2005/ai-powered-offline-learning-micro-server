import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: '0.0.0.0',   // Listen on all interfaces — allows phones on the same Wi-Fi to connect
    proxy: {
      '/api': {
        target: 'http://localhost:5000',  // Proxy runs server-side, so localhost = the dev machine
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../backend/static/dist',
    emptyOutDir: true,
  },
})

