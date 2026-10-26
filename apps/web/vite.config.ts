import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      // 契约生成的类型放在 packages/contracts，只读
      '@cw/contracts': fileURLToPath(
        new URL('../../packages/contracts/src/types.ts', import.meta.url),
      ),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 前端只调 /api，代理到后端；不要在前端硬编码后端域名
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
