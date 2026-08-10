<template>
  <n-config-provider
    :theme="themeStore.theme === 'dark' ? darkTheme : null"
    :theme-overrides="themeOverrides"
    :locale="zhCN"
    :date-locale="dateZhCN"
  >
    <n-message-provider>
      <n-notification-provider>
        <router-view />
      </n-notification-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { watch, onMounted, computed } from 'vue'
import { darkTheme, zhCN, dateZhCN } from 'naive-ui'
import type { GlobalThemeOverrides } from 'naive-ui'
import { useAccountStore, useResourceStore, useThemeStore } from '@/store'

const themeStore = useThemeStore()
const accountStore = useAccountStore()
const resourceStore = useResourceStore()

onMounted(async () => {
  themeStore.initTheme()
  try {
    await accountStore.loadAccounts()
    await resourceStore.loadAllResources()
  } catch (e) {}
})

// 监听主题变化并设置到 html 根节点以驱动 Tailwind CSS 的 dark: 样式
watch(
  () => themeStore.theme,
  (newTheme) => {
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  },
  { immediate: true }
)

const themeOverrides = computed<GlobalThemeOverrides>(() => {
  const isDark = themeStore.theme === 'dark'
  return {
    common: {
      primaryColor: '#1677ff',      // 经典 Ant Design 蓝
      primaryColorHover: '#40a9ff',
      primaryColorPressed: '#096dd9',
      successColor: '#52c41a',      // 绿
      warningColor: '#faad14',      // 黄
      errorColor: '#ff4d4f',        // 红
      borderRadius: '12px',
      borderRadiusSmall: '8px',
      fontFamily: "'Outfit', 'Inter', system-ui, -apple-system, sans-serif",
      fontSize: '14px',
      bodyColor: isDark ? '#0f172a' : '#f5f7fa',
      cardColor: isDark ? '#111827' : '#ffffff',
      borderColor: isDark ? '#1f2937' : '#e5e7eb',
    },
    Card: {
      borderRadius: '12px',
    },
    Button: {
      borderRadiusMedium: '8px',
      borderRadiusSmall: '6px',
    },
    DataTable: {
      borderRadius: '12px',
    },
    Tag: {
      borderRadius: '6px',
    },
  }
})
</script>
