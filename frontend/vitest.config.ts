import { defineConfig } from 'vitest/config'
import path from 'path'

export default defineConfig({
  resolve: { alias: { '@': path.resolve(__dirname) } },
  esbuild: { jsx: 'automatic' },
  test: {
    include: ['lib/**/*.test.ts', 'components/**/*.test.tsx'],
    exclude: ['node_modules', '.next'],
  },
})
