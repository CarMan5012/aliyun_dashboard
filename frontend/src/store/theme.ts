import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<'light' | 'dark'>('dark') // 默认深色优先

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    localStorage.setItem('aliyun-dashboard-theme', theme.value)
    applyTheme()
  }

  function initTheme() {
    const saved = localStorage.getItem('aliyun-dashboard-theme')
    if (saved === 'light' || saved === 'dark') {
      theme.value = saved
    } else {
      theme.value = 'dark' // 默认
    }
    applyTheme()
  }

  function applyTheme() {
    if (theme.value === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  return {
    theme,
    toggleTheme,
    initTheme,
  }
})
