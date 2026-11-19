import {defineConfig} from 'vite';

const backend = 'http://127.0.0.1:8765';

export default defineConfig({
  server: {
    proxy: {
      '/api': {
        target: backend,
        changeOrigin: true,
        headers: {origin: backend},
      },
    },
  },
});
