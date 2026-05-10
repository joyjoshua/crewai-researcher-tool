import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Use 127.0.0.1 (not "localhost") — on Windows, Node resolves localhost to ::1
      // first; Uvicorn is often bound only to 127.0.0.1, causing ECONNREFUSED / 502.
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
