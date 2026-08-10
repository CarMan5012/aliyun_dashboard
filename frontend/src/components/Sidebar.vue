<template>
  <aside
    class="bg-white dark:bg-cardDark border-r border-borderLight dark:border-borderDark h-screen flex flex-col justify-between transition-all duration-300 z-30 flex-shrink-0"
    :class="[resourceStore.sidebarCollapsed ? 'w-[64px]' : 'w-[220px]']"
  >
    <!-- Logo 区域 -->
    <div class="h-[64px] flex items-center px-4 border-b border-borderLight dark:border-borderDark overflow-hidden flex-shrink-0">
      <div class="flex items-center gap-3 min-w-[200px]">
        <div class="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0 shadow-sm">
          <Icon icon="lucide:cloud" :width="18" />
        </div>
        <span
          v-show="!resourceStore.sidebarCollapsed"
          class="font-bold text-sm tracking-wide text-slate-800 dark:text-slate-100 whitespace-nowrap"
        >
          云资源管理平台
        </span>
      </div>
    </div>

    <!-- 导航菜单 -->
    <nav class="flex-1 px-3 py-4 space-y-1.5 overflow-y-auto">
      <div
        v-for="item in menuItems"
        :key="item.path"
        @click="navigateTo(item.path)"
        class="flex items-center gap-3 px-3.5 py-2.5 rounded-lg transition-all duration-200 cursor-pointer group no-underline border font-normal select-none"
        :class="[
          isItemActive(item.path)
            ? 'bg-primary/10 text-primary border-primary/20'
            : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/40 border-transparent'
        ]"
      >
        <Icon :icon="item.icon" :width="19" class="flex-shrink-0 group-hover:scale-105 transition" />
        <span v-show="!resourceStore.sidebarCollapsed" class="text-[15px] font-normal whitespace-nowrap">{{ item.name }}</span>
      </div>
    </nav>

    <!-- 底部区域 (主题切换 & 折叠 & 版本) -->
    <div class="p-3 border-t border-borderLight dark:border-borderDark space-y-3">
      <!-- 切换主题 -->
      <button
        @click="themeStore.toggleTheme()"
        class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/40 transition-all duration-200 bg-transparent border-0 cursor-pointer text-left font-normal"
        title="切换主题"
      >
        <Icon
          :icon="themeStore.theme === 'dark' ? 'lucide:sun' : 'lucide:moon'"
          :width="19"
          class="text-amber-500 flex-shrink-0"
        />
        <span v-show="!resourceStore.sidebarCollapsed" class="text-[15px] font-normal whitespace-nowrap">
          {{ themeStore.theme === 'dark' ? '浅色模式' : '深色模式' }}
        </span>
      </button>

      <!-- 折叠侧边栏 -->
      <button
        @click="resourceStore.sidebarCollapsed = !resourceStore.sidebarCollapsed"
        class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/40 transition-all duration-200 bg-transparent border-0 cursor-pointer text-left font-normal"
      >
        <Icon
          :icon="resourceStore.sidebarCollapsed ? 'lucide:chevron-right' : 'lucide:chevron-left'"
          :width="19"
          class="flex-shrink-0"
        />
        <span v-show="!resourceStore.sidebarCollapsed" class="text-[15px] font-normal whitespace-nowrap">收起侧栏</span>
      </button>

      <!-- 系统版本 -->
      <div
        v-show="!resourceStore.sidebarCollapsed"
        class="text-center text-[11px] text-slate-400 dark:text-slate-600 font-mono select-none"
      >
        Version 2.1.0
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { useRoute, useRouter } from 'vue-router'
import { useThemeStore, useResourceStore } from '@/store'

const themeStore = useThemeStore()
const resourceStore = useResourceStore()
const route = useRoute()
const router = useRouter()

const navigateTo = (path: string) => {
  router.push(path)
}

const isItemActive = (path: string) => {
  if (path.includes('?')) {
    const [basePath, queryStr] = path.split('?')
    const targetTab = new URLSearchParams(queryStr).get('tab')
    const currentTab = route.query.tab || (route.path === '/resources' ? 'ECS' : null)
    return route.path === basePath && currentTab === targetTab
  }
  return route.path === path
}

const menuItems = [
  { name: '仪表盘', path: '/dashboard', icon: 'lucide:layout-dashboard' },
  { name: '云服务器', path: '/resources?tab=ECS', icon: 'lucide:server' },
  { name: '弹性公网IP', path: '/resources?tab=EIP', icon: 'lucide:globe' },
  { name: '域名管理', path: '/resources?tab=Domain', icon: 'lucide:link' },
  { name: 'SSL证书', path: '/resources?tab=SSL', icon: 'lucide:shield-check' },
  { name: '同步中心', path: '/sync', icon: 'lucide:refresh-cw' },
  { name: '云账号管理', path: '/accounts', icon: 'lucide:users' },
  { name: '系统配置', path: '/settings', icon: 'lucide:settings' },
]
</script>

<style scoped>
/* Remove active class override since class binding handles it cleanly */
</style>
