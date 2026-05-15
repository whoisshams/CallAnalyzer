import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Proxy the Whisper transcription server so the browser sees it as same-origin.
    // The container on :9000 has no CORS support, so direct calls from :5173 fail.
    proxy: {
      '/whisper': {
        target: 'http://localhost:9000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/whisper/, ''),
      },
    },
  },
})
