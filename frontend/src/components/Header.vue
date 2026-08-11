<template>
  <header class="h-[64px] flex items-center justify-between px-6 bg-white dark:bg-cardDark border-b border-borderLight dark:border-borderDark flex-shrink-0 z-20 transition-colors duration-300">
    <!-- 左侧：系统 Logo 与系统名称 / 面包屑 -->
    <div class="flex items-center gap-3">
      <div v-if="resourceStore.sidebarCollapsed" class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
          <Icon icon="lucide:cloud" :width="18" />
        </div>
        <span class="font-bold text-sm text-slate-800 dark:text-slate-100 whitespace-nowrap">云资源管理平台</span>
      </div>
      <div v-else class="flex items-center gap-2">
        <span class="text-xs font-semibold text-slate-400 dark:text-slate-500">控制台</span>
        <span class="text-slate-350 dark:text-slate-700">/</span>
        <span class="text-xs font-semibold text-slate-700 dark:text-slate-200">{{ currentRouteName }}</span>
      </div>
    </div>

    <!-- 右侧：全局搜索 & 账号切换 & 同步状态 & 通知 & 头像 -->
    <div class="flex items-center gap-4">
      <!-- 全局搜索 -->
      <div class="flex items-center gap-2">
        <n-input
          v-model:value="resourceStore.searchKeyword"
          placeholder="搜索 IP、域名、主机..."
          size="medium"
          clearable
          class="w-56 bg-slate-50 dark:bg-slate-900 border-borderLight dark:border-borderDark rounded-lg"
          @keyup.enter="resourceStore.performGlobalSearch()"
          @clear="resourceStore.clearSearch()"
        >
          <template #prefix>
            <Icon icon="lucide:search" :width="14" class="text-slate-400" />
          </template>
        </n-input>
        <n-button
          type="primary"
          size="medium"
          @click="resourceStore.performGlobalSearch()"
        >
          搜索
        </n-button>
      </div>

      <!-- 账号切换 -->
      <n-select
        :value="accountStore.activeAccountId"
        :options="accountOptions"
        size="medium"
        style="width: 220px"
        @update:value="onAccountChange"
      />

      <!-- 立即同步按钮 -->
      <n-button
        size="medium"
        type="primary"
        :loading="syncStore.globalSyncing"
        @click="handleSync"
        class="shadow-sm font-semibold"
      >
        <template #icon>
          <Icon icon="lucide:refresh-cw" :width="14" />
        </template>
        立即同步
      </n-button>

      <!-- 消息警报 -->
      <div class="relative cursor-pointer p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800/60 text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 transition">
        <n-popover trigger="click" placement="bottom-end" width="320">
          <template #trigger>
            <n-badge :value="notificationStore.unreadCount" :max="99" type="warning" :show="notificationStore.unreadCount > 0">
              <Icon icon="lucide:bell" :width="18" />
            </n-badge>
          </template>
          <div class="p-2 space-y-3">
            <h4 class="font-bold text-sm text-slate-800 dark:text-slate-200 border-b border-borderLight dark:border-borderDark pb-1.5 flex justify-between">
              <span>到期预警列表</span>
              <span class="text-xs text-yellow-500 font-normal">阈值: {{ settingStore.warningDaysThreshold }}天</span>
            </h4>
            <div v-if="notificationStore.unreadCount === 0" class="text-xs text-slate-400 dark:text-slate-500 text-center py-4">
              暂无临期过期资源警报
            </div>
            <div v-else class="space-y-2 max-h-[250px] overflow-y-auto pr-1">
              <!-- 临期域名 -->
              <div v-for="d in notificationStore.warningDomains" :key="d.id" class="text-xs p-2 bg-slate-50 dark:bg-slate-900 border border-borderLight dark:border-borderDark rounded-lg hover:border-yellow-500/30 transition">
                <div class="font-semibold text-slate-700 dark:text-slate-300 flex justify-between">
                  <span>{{ d.details.domain_name }}</span>
                  <span class="text-rose-500 font-bold">域名临期</span>
                </div>
                <div class="text-[10px] text-slate-400 dark:text-slate-500 mt-1">到期日: {{ d.details.expiration_date }}</div>
              </div>
              <!-- 临期证书 -->
              <div v-for="c in notificationStore.warningCerts" :key="c.id" class="text-xs p-2 bg-slate-50 dark:bg-slate-900 border border-borderLight dark:border-borderDark rounded-lg hover:border-yellow-500/30 transition">
                <div class="font-semibold text-slate-700 dark:text-slate-300 flex justify-between">
                  <span>{{ c.details.cert_name }}</span>
                  <span class="text-amber-500 font-bold">证书临期</span>
                </div>
                <div class="text-[10px] text-slate-400 dark:text-slate-500 mt-1">到期日: {{ c.details.cert_end_time }}</div>
              </div>
            </div>
          </div>
        </n-popover>
      </div>

      <!-- 用户信息 -->
      <div class="flex items-center gap-2.5 border-l border-borderLight dark:border-borderDark pl-4">
        <img :src="authStore.user.avatar" class="w-8 h-8 rounded-full border border-borderLight dark:border-borderDark bg-slate-100 dark:bg-slate-950/40 p-0.5" />
        <div class="hidden md:flex flex-col select-none">
          <span class="text-xs font-semibold text-slate-700 dark:text-slate-300">{{ authStore.user.username }}</span>
          <span class="text-[10px] text-slate-400 dark:text-slate-500 font-medium">{{ authStore.user.role }}</span>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Icon } from '@iconify/vue'
import { useMessage } from 'naive-ui'
import { useRoute } from 'vue-router'
import {
  useAccountStore,
  useResourceStore,
  useSyncStore,
  useNotificationStore,
  useAuthStore,
  useSettingStore,
} from '@/store'

const route = useRoute()
const accountStore = useAccountStore()
const resourceStore = useResourceStore()
const syncStore = useSyncStore()
const notificationStore = useNotificationStore()
const authStore = useAuthStore()
const settingStore = useSettingStore()
const message = useMessage()

const currentRouteName = computed(() => {
  if (route.path === '/dashboard') return '仪表盘'
  if (route.path === '/resources') {
    const tab = route.query.tab || 'ECS'
    if (tab === 'ECS') return '云服务器 ECS'
    if (tab === 'EIP') return '弹性公网IP'
    if (tab === 'Domain') return '域名管理'
    if (tab === 'SSL') return 'SSL 证书'
    return '云服务器 ECS'
  }
  if (route.path === '/sync') return '同步中心'
  if (route.path === '/accounts') return '云账号管理'
  if (route.path === '/settings') return '系统配置'
  return '控制台'
})

const accountOptions = computed(() => {
  const list = accountStore.accounts.map((a) => ({
    label: a.account_alias,
    value: a.id,
  }))
  return [{ label: '全部账号', value: null }, ...list]
})

async function onAccountChange(val: number | null) {
  accountStore.activeAccountId = val
  if (val === null) {
    accountStore.activeAccount = '全部账号'
  } else {
    const acc = accountStore.accounts.find(a => a.id === val)
    if (acc) {
      accountStore.activeAccount = acc.account_alias
    }
  }
  await resourceStore.loadAllResources(true)
}

async function handleSync() {
  try {
    message.info('开始同步全局资产')
    await syncStore.triggerGlobalSync()
    message.success('已派发同步命令，同步进度请在看板顶部查看')
  } catch (e) {
    message.error('同步失败')
  }
}
</script>

