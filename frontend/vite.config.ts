import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

<<<<<<< HEAD
export default defineConfig({
  plugins: [react(), tailwindcss()],
})
=======
// Cible du proxy : "backend:8000" dans Docker, "localhost:8000" en dev local
const API_TARGET = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Sans ça, les fetch("/api/v1/...") tapent le serveur Vite et renvoient 404
      '/api': {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
})
>>>>>>> ada8cf0c4c914634ec52f3e8795979bbf9320122
