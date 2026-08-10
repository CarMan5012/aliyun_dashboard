/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Outfit', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        brand: {
          50:  '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
        surface: {
          0:   '#ffffff',
          50:  '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
        },
        primary: '#1677ff',     // 蓝 (Ant Design Blue)
        success: '#52c41a',     // 绿
        warning: '#faad14',     // 黄
        danger: '#ff4d4f',      // 红
        bgDark: '#0f172a',      // slate-900 背景
        cardDark: '#111827',    // gray-900 卡片
        borderDark: '#1f2937',  // gray-800 边框
        bgLight: '#f5f7fa',     // 浅色背景
        cardLight: '#ffffff',   // 浅色卡片
        borderLight: '#e5e7eb'  // 浅色边框
      },
      boxShadow: {
        card: '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
        'card-hover': '0 10px 25px rgba(0,0,0,0.08), 0 4px 10px rgba(0,0,0,0.04)',
        panel: '0 0 0 1px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.06)',
      },
      borderRadius: {
        xl: '14px',
        '2xl': '18px',
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: false, // Naive UI 自带重置样式，避免冲突
  },
}
