import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    tailwindcss(),
    react(),
  ],
  server: {
    host: '0.0.0.0',   // required for Docker container networking
    port: 5173,
    proxy: {
      '/api': {
        // In Docker, the browser hits localhost:5173 which proxies to the backend container
        // VITE_API_URL overrides this for direct API calls from the browser
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
