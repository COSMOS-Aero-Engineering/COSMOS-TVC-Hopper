// 화면이 둘이다: index.html(3D 뷰어)과 thrust.html(실험 A 추력 곡선).
import { resolve } from 'node:path';
import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(import.meta.dirname, 'index.html'),
        thrust: resolve(import.meta.dirname, 'thrust.html'),
      },
    },
  },
});
