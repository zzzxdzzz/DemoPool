import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/locations': 'http://localhost:8000',
      '/posts': 'http://localhost:8000',
      '/comments': 'http://localhost:8000',
      '/sessions': 'http://localhost:8000',
      '/upload': 'http://localhost:8000',
      '/static': 'http://localhost:8000',
    }
  }
})
