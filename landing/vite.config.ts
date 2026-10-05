import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo, `npm run dev` reenvía al backend local solo lo que la landing usa.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    proxy: {
      '/api/v1/sitio': { target: 'http://localhost:8000', changeOrigin: false },
      '/uploads/condominios': { target: 'http://localhost:8000', changeOrigin: false },
    },
  },
})
