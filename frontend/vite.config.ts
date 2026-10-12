import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// In dev the browser talks only to Vite, which forwards /api to the FastAPI backend.
const backend = process.env.POLTRACKER_API ?? 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  test: { environment: 'jsdom', setupFiles: ['./src/test/setup.ts'], css: false, restoreMocks: true },
  server: {
    fs: { allow: ['..'] }, // PRIVACY.md at the repository root is the one source of the in-app privacy page
    proxy: {
      '/api': { target: backend, changeOrigin: true, rewrite: (path) => path.replace(/^\/api/, '') },
    },
  },
});
