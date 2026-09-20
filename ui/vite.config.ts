import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The API port is read when the dev server starts (this file runs in Node), so it can be set
// at runtime: `SOURCETEXT_API_PORT=9000 npm run dev`. Built UIs use relative /api URLs and need no port.
const apiPort = process.env.SOURCETEXT_API_PORT ?? '8001'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: { '/api': `http://localhost:${apiPort}` },
  },
})
