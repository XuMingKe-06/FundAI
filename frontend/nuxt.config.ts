import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import compression from 'vite-plugin-compression'

export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',

  devtools: {
    enabled: process.env.NODE_ENV === 'development'
  },

  app: {
    head: {
      title: 'FundAI - 多智能体场外基金分析决策系统',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: '基于AI多智能体协作，为您提供经过成本校验的短线与长线投资建议' }
      ],
      link: []
    }
  },

  css: [
    '~/assets/css/global.css'
  ],

  modules: [
    '@pinia/nuxt'
  ],

  plugins: [
    '~/plugins/element-plus.ts'
  ],

  vite: {
    plugins: [
      AutoImport({
        resolvers: [ElementPlusResolver()],
        dts: 'types/auto-imports.d.ts',
      }),
      Components({
        resolvers: [ElementPlusResolver()],
        dts: 'types/components.d.ts',
      }),
      compression({
        algorithm: 'gzip',
        ext: '.gz',
        threshold: 10240,
        deleteOriginFile: false,
      }),
      compression({
        algorithm: 'brotliCompress',
        ext: '.br',
        threshold: 10240,
        deleteOriginFile: false,
      }),
    ],
    ssr: {
      noExternal: ['element-plus']
    },
    optimizeDeps: {
      include: [
        '@vue/devtools-core',
        '@vue/devtools-kit',
        'element-plus',
        'element-plus/es/locale/lang/zh-cn',
        'echarts',
        'echarts/core',
        'echarts/charts',
        'echarts/components',
        'echarts/renderers',
        'echarts/features',
        'vue-echarts',
        'axios',
        'markdown-it',
        'element-plus/es/components/dialog/style/css',
        'element-plus/es/components/button/style/css',
        'element-plus/es/components/form/style/css',
        'element-plus/es/components/form-item/style/css',
        'element-plus/es/components/radio-group/style/css',
        'element-plus/es/components/radio/style/css',
        'element-plus/es/components/input-number/style/css',
        'element-plus/es/components/select/style/css',
        'element-plus/es/components/option/style/css',
        'element-plus/es/components/card/style/css',
        'element-plus/es/components/tag/style/css',
        'element-plus/es/components/input/style/css',
        'element-plus/es/components/divider/style/css',
        'element-plus/es/components/message-box/style/css',
        'element-plus/es/components/message/style/css',
      ],
      exclude: []
    },
    build: {
      chunkSizeWarningLimit: 1500,
      rollupOptions: {
        output: {
          chunkFileNames: 'js/[name]-[hash].js',
          entryFileNames: 'js/[name]-[hash].js',
          assetFileNames: '[ext]/[name]-[hash].[ext]',
          manualChunks: (id) => {
            if (id.includes('node_modules')) {
              if (id.includes('element-plus')) {
                return 'element-plus'
              }
              if (id.includes('echarts') || id.includes('vue-echarts')) {
                return 'echarts'
              }
              if (id.includes('pinia') || id.includes('@pinia')) {
                return 'pinia'
              }
            }
          }
        }
      },
      minify: 'esbuild',
      cssMinify: true,
    }
  },

  typescript: {
    strict: true
  },

  nitro: {
    compressPublicAssets: true,
  },

  features: {
    inlineStyles: false,
  },

  experimental: {
    payloadExtraction: false,
  },

  routeRules: {
    '/': { prerender: true },
    '/workspace': { ssr: false },
  },
})
