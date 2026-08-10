<template>
  <div class="space-y-4">
    <!-- 头部欢迎语与全局进度状态 -->
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white/90 dark:bg-cardDark/90 border border-slate-200/80 dark:border-slate-700/70 px-4 py-3.5 rounded-lg shadow-sm">
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">云资产监控中心</h1>
            </div>
            <p class="mt-0.5 text-xs leading-4 text-slate-500 dark:text-slate-400 font-medium">
              您当前已绑定了 {{ accountStore.accounts.length }} 个云账号，当前过滤视图：{{ accountStore.activeAccount }}。
            </p>
          </div>
          
          <!-- 同步进度提示 (如果有任务在运行) -->
          <div v-if="syncStore.syncing" class="flex items-center gap-3 bg-primary/10 border border-primary/20 px-4 py-2.5 rounded-xl">
            <Icon icon="lucide:refresh-cw" class="animate-spin text-primary" :width="16" />
            <span class="text-xs text-primary font-semibold font-mono">资产刷新中... 已耗时 {{ syncStore.syncTimeElapsed }} 秒</span>
            <n-button size="tiny" quaternary type="error" @click="syncStore.stopTracking()">停止跟踪</n-button>
          </div>
        </div>

        <!-- 四个指标统计卡片 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <StatCard title="云服务器 ECS" :value="resourceStore.ecsList.length" icon="lucide:server" iconColor="text-primary" />
          <StatCard title="弹性公网 IP" :value="resourceStore.eipList.length" icon="lucide:globe" iconColor="text-indigo-500" />
          <StatCard title="域名资产" :value="resourceStore.domainList.length" icon="lucide:link-2" iconColor="text-success" />
          <StatCard title="SSL 证书" :value="resourceStore.sslList.length" icon="lucide:shield-check" iconColor="text-amber-500" />
        </div>

        <section class="account-sync-overview bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl p-5">
          <div class="flex items-start justify-between gap-4 mb-4">
            <div>
              <h3 class="text-sm font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                <Icon icon="lucide:database-zap" :width="14" class="text-primary" />
                云账号资源同步概览
              </h3>
              <p class="mt-1 text-[10.5px] text-slate-400 dark:text-slate-500">按账号展示最近一次 ECS、EIP、域名和 SSL 同步结果</p>
            </div>
            <span class="text-[10px] font-medium text-slate-400 dark:text-slate-500">{{ accountStore.accounts.length }} 个账号</span>
          </div>

          <div v-if="accountStore.accounts.length" class="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-4 gap-3">
            <article
              v-for="account in accountStore.accounts"
              :key="`sync-overview-${account.id}`"
              class="account-sync-card rounded-lg border border-slate-200/80 dark:border-slate-700/70 bg-slate-50/70 dark:bg-slate-900/35 p-3.5"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <h4 class="truncate text-[12px] font-semibold text-slate-800 dark:text-slate-100" :title="account.account_alias">{{ account.account_alias }}</h4>
                  <p class="mt-0.5 text-[9.5px] text-slate-400 dark:text-slate-500">成功同步 {{ getAccountResourceTotal(account) }} 项资源</p>
                </div>
                <n-tag size="tiny" :type="getAccountSyncTag(account.last_sync_status)" :bordered="false">
                  {{ getAccountSyncLabel(account.last_sync_status) }}
                </n-tag>
              </div>

              <div class="mt-3 grid grid-cols-4 gap-1.5">
                <div
                  v-for="service in syncServices"
                  :key="service.key"
                  class="service-stat rounded-md bg-white dark:bg-slate-800/65 px-1.5 py-2 text-center"
                  :title="getServiceError(account, service.key)"
                >
                  <div class="text-[9px] font-medium text-slate-400 dark:text-slate-500">{{ service.label }}</div>
                  <div class="mt-0.5 text-[12px] font-semibold tabular-nums" :class="getServiceValueClass(account, service.key)">
                    {{ getServiceValue(account, service.key) }}
                  </div>
                </div>
              </div>

              <div class="mt-2.5 pt-2 border-t border-slate-200/60 dark:border-slate-700/50">
                <div class="flex items-center justify-between mb-1">
                  <span class="text-[9.5px] font-medium text-slate-400 dark:text-slate-500 flex items-center gap-1">
                    <Icon icon="lucide:map-pin" :width="11" class="text-sky-500" />
                    活跃同步地域 ({{ (account.active_regions || []).length }}个)
                  </span>
                </div>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="reg in (account.active_regions || [])"
                    :key="reg"
                    class="inline-block px-1.5 py-0.5 rounded bg-sky-500/10 dark:bg-sky-500/15 text-sky-600 dark:text-sky-400 text-[9px] font-normal font-mono leading-none"
                  >
                    {{ getRegionName(reg) }}
                  </span>
                  <span v-if="!account.active_regions || account.active_regions.length === 0" class="text-[9.5px] text-slate-400">默认主地域</span>
                </div>
              </div>

              <div class="mt-2.5 flex items-center justify-between border-t border-slate-200/70 dark:border-slate-700/60 pt-2.5 text-[9.5px] text-slate-400 dark:text-slate-500">
                <span>最近成功</span>
                <span class="font-mono tabular-nums">{{ formatSyncTime(account.last_synced_at) }}</span>
              </div>
            </article>
          </div>
          <div v-else class="py-8 text-center text-xs text-slate-400">暂无云账号</div>
        </section>

        <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 shadow-sm">
          <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5 uppercase tracking-wider mb-4">
            <Icon icon="lucide:cloud-cog" :width="14" />
            云账号最近同步情况
          </h3>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead class="text-left text-slate-400 border-b border-borderLight dark:border-borderDark">
                <tr>
                  <th class="py-2 pr-4">云账号</th>
                  <th class="py-2 pr-4">最近状态</th>
                  <th class="py-2 pr-4">活跃同步地域</th>
                  <th class="py-2 pr-4">最近尝试</th>
                  <th class="py-2 pr-4">最近成功</th>
                  <th class="py-2">结果摘要</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="account in accountStore.accounts" :key="account.id" class="border-b last:border-0 border-borderLight dark:border-borderDark">
                  <td class="py-3 pr-4 font-semibold text-slate-700 dark:text-slate-300">{{ account.account_alias }}</td>
                  <td class="py-3 pr-4">
                    <n-tag size="small" :type="getAccountSyncTag(account.last_sync_status)">
                      {{ getAccountSyncLabel(account.last_sync_status) }}
                    </n-tag>
                  </td>
                  <td class="py-3 pr-4">
                    <div class="flex flex-wrap gap-1 max-w-[220px]">
                      <span
                        v-for="reg in (account.active_regions || [])"
                        :key="reg"
                        class="inline-block px-1.5 py-0.5 rounded bg-sky-500/10 dark:bg-sky-500/15 text-sky-600 dark:text-sky-400 text-[9px] font-normal font-mono leading-none"
                      >
                        {{ getRegionName(reg) }}
                      </span>
                    </div>
                  </td>
                  <td class="py-3 pr-4 whitespace-nowrap">{{ formatSyncTime(account.last_attempted_at) }}</td>
                  <td class="py-3 pr-4 whitespace-nowrap">{{ formatSyncTime(account.last_synced_at) }}</td>
                  <td class="py-3 max-w-[420px] truncate font-medium text-slate-600 dark:text-slate-300" :title="getFormattedSyncSummary(account)">
                    {{ getFormattedSyncSummary(account) }}
                  </td>
                </tr>
                <tr v-if="accountStore.accounts.length === 0">
                  <td colspan="6" class="py-8 text-center text-slate-400">暂无云账号</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 两栏布局：左图表/警报，右时间轴 -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- 左侧 2/3：图表与过期警告 -->
          <div class="lg:col-span-2 space-y-6">
            <!-- 资源分布与到期预警 -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <!-- ECharts 饼图 -->
              <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 flex flex-col justify-between shadow-sm">
                <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5 uppercase tracking-wider mb-4">
                  <Icon icon="lucide:pie-chart" :width="14" />
                  资产类型分布比例
                </h3>
                <div class="flex-grow flex items-center justify-center">
                  <EchartsPie :data="pieData" title="资产占比" />
                </div>
              </div>

              <!-- 到期警报卡片 -->
              <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 flex flex-col justify-between shadow-sm">
                <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5 uppercase tracking-wider mb-4">
                  <Icon icon="lucide:alert-triangle" :width="14" class="text-amber-550 dark:text-warning" />
                  临期过期警报资源 ({{ notificationStore.unreadCount }})
                </h3>
                <div class="flex-grow overflow-y-auto max-h-[220px] space-y-2 pr-1 custom-scroll">
                  <div v-if="notificationStore.unreadCount === 0" class="text-xs text-slate-450 dark:text-slate-550 text-center py-12">
                    暂无临期过期警报资源，安全状态良好。
                  </div>
                  <div v-else class="space-y-2">
                    <!-- 到期域名 -->
                    <div v-for="d in notificationStore.warningDomains" :key="d.id" class="p-3 bg-slate-50 dark:bg-slate-900/50 border border-borderLight dark:border-borderDark rounded-lg flex items-center justify-between hover:border-amber-500/20 transition duration-200">
                      <div>
                        <div class="text-xs font-bold text-slate-700 dark:text-slate-200">{{ d.details.domain_name }}</div>
                        <div class="text-[10px] text-slate-400 dark:text-slate-500 mt-1 font-mono">过期日: {{ d.details.expiration_date }}</div>
                      </div>
                      <n-tag size="small" :type="getAlertLevel(d.details.expiration_date)">{{ getRemainingDaysText(d.details.expiration_date) }}</n-tag>
                    </div>

                    <!-- 到期证书 -->
                    <div v-for="c in notificationStore.warningCerts" :key="c.id" class="p-3 bg-slate-50 dark:bg-slate-900/50 border border-borderLight dark:border-borderDark rounded-lg flex items-center justify-between hover:border-amber-500/20 transition duration-200">
                      <div>
                        <div class="text-xs font-bold text-slate-700 dark:text-slate-200">{{ c.details.cert_name }}</div>
                        <div class="text-[10px] text-slate-400 dark:text-slate-500 mt-1 font-mono">过期日: {{ c.details.cert_end_time }}</div>
                      </div>
                      <n-tag size="small" :type="getAlertLevel(c.details.cert_end_time)">{{ getRemainingDaysText(c.details.cert_end_time) }}</n-tag>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧 1/3：最近同步时间轴 -->
          <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 flex flex-col shadow-sm">
            <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5 uppercase tracking-wider mb-6">
              <Icon icon="lucide:history" :width="14" />
              同步活动历史流水
            </h3>
            <div class="flex-grow overflow-y-auto max-h-[300px] pr-1 custom-scroll">
              <div v-if="syncStore.syncHistory.length === 0" class="text-xs text-slate-450 dark:text-slate-550 text-center py-20">
                暂无资源同步记录，请点击顶栏手动刷新
              </div>
              <n-timeline v-else class="pl-2">
                <n-timeline-item
                  v-for="log in syncStore.syncHistory.slice(0, 5)"
                  :key="log.id"
                  :type="getTimelineType(log.status)"
                  :title="getTimelineTitle(log)"
                  :time="log.start_time"
                >
                </n-timeline-item>
              </n-timeline>
            </div>
          </div>
        </div>
      </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useAccountStore, useResourceStore, useSyncStore, useNotificationStore, useSettingStore } from '@/store'
import StatCard from '@/components/StatCard.vue'
import EchartsPie from '@/components/EchartsPie.vue'
import dayjs from 'dayjs'

const accountStore = useAccountStore()
const resourceStore = useResourceStore()
const syncStore = useSyncStore()
const notificationStore = useNotificationStore()
const settingStore = useSettingStore()

onMounted(async () => {
  await accountStore.loadAccounts()
  await resourceStore.loadAllResources()
  syncStore.loadHistory()
  settingStore.loadSettings()
})

const pieData = computed(() => {
  return [
    { name: 'ECS 实例', value: resourceStore.ecsList.length },
    { name: '弹性公网 IP', value: resourceStore.eipList.length },
    { name: '域名资产', value: resourceStore.domainList.length },
    { name: 'SSL 证书', value: resourceStore.sslList.length },
  ]
})

const syncServices = [
  { key: 'ECS', label: 'ECS' },
  { key: 'EIP', label: 'EIP' },
  { key: 'Domain', label: '域名' },
  { key: 'SSL', label: 'SSL' },
] as const

function getServiceResult(account: any, service: string): any {
  return account.last_sync_details?.[service]
}

function getServiceValue(account: any, service: string): number | string {
  const result = getServiceResult(account, service)
  if (!result) return '-'
  return result.status === 'success' ? result.count ?? 0 : '失败'
}

function getServiceValueClass(account: any, service: string): string {
  const result = getServiceResult(account, service)
  if (!result) return 'text-slate-400'
  return result.status === 'success' ? 'text-slate-700 dark:text-slate-200' : 'text-rose-500'
}

function getServiceError(account: any, service: string): string {
  const result = getServiceResult(account, service)
  return result?.error || `${service}：${getServiceValue(account, service)}`
}

function getAccountResourceTotal(account: any): number {
  return syncServices.reduce((total, service) => {
    const result = getServiceResult(account, service.key)
    return total + (result?.status === 'success' ? Number(result.count || 0) : 0)
  }, 0)
}

function getRemainingDays(expDate?: string): number {
  if (!expDate) return 999
  return dayjs(expDate).startOf('day').diff(dayjs().startOf('day'), 'day')
}

function formatSyncTime(value?: string): string {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'
}

function getAccountSyncTag(status?: string): 'success' | 'warning' | 'error' | 'default' {
  if (status === 'success') return 'success'
  if (status === 'partial_failure') return 'warning'
  if (status === 'failure') return 'error'
  return 'default'
}

const regionNameMap: Record<string, string> = {
  'cn-hangzhou': '华东1 (杭州)',
  'cn-beijing': '华北2 (北京)',
  'cn-shanghai': '华东2 (上海)',
  'cn-shenzhen': '华南1 (深圳)',
  'cn-hongkong': '中国香港',
  'cn-qingdao': '华北1 (青岛)',
  'cn-zhangjiakou': '华北3 (张家口)',
  'cn-huhehaote': '华北5 (呼和浩特)',
  'cn-wulanchabu': '华北6 (乌兰察布)',
  'cn-nanjing': '华东5 (南京)',
  'cn-fuzhou': '华东6 (福州)',
  'cn-guangzhou': '华南2 (广州)',
  'cn-chengdu': '西南1 (成都)',
  'us-west-1': '美西 (硅谷)',
  'us-east-1': '美东 (弗吉尼亚)',
  'ap-southeast-1': '新加坡',
  'ap-northeast-1': '东京',
}

function getRegionName(regionId: string): string {
  return regionNameMap[regionId] || regionId
}

function getAccountSyncLabel(status?: string): string {
  if (status === 'success') return '成功'
  if (status === 'partial_failure') return '部分失败'
  if (status === 'failure') return '失败'
  return '未同步'
}

function getFormattedSyncSummary(account: any): string {
  if (!account.last_sync_status || account.last_sync_status === 'none') {
    return '尚未执行同步'
  }
  if (account.last_sync_status === 'failure') {
    return account.last_sync_error || '全量同步失败'
  }

  const details = account.last_sync_details || {}
  const services = [
    { key: 'ECS', label: 'ECS' },
    { key: 'EIP', label: 'EIP' },
    { key: 'Domain', label: '域名' },
    { key: 'SSL', label: 'SSL' }
  ]

  const parts: string[] = []
  for (const s of services) {
    const res = details[s.key]
    if (!res) continue
    if (res.status === 'success') {
      parts.push(`${s.label}同步成功`)
    } else if (res.status === 'failed' || res.status === 'failure') {
      parts.push(`${s.label}同步失败`)
    } else {
      parts.push(`${s.label}${res.status || '未执行'}`)
    }
  }

  return parts.length > 0 ? parts.join('，') : (account.last_sync_error || '全量同步成功')
}

function getRemainingDaysText(expDate?: string): string {
  const days = getRemainingDays(expDate)
  if (days < 0) return '已过期'
  return `${days} 天后过期`
}

function getAlertLevel(expDate?: string): 'error' | 'warning' | 'info' {
  const days = getRemainingDays(expDate)
  if (days <= settingStore.criticalDays) return 'error'
  if (days <= settingStore.warningDays) return 'warning'
  return 'info'
}

function getTimelineTitle(log: any): string {
  const alias = log.account_alias || '全局全量同步'
  if (log.status === 'success') return `${alias} 同步成功`
  if (log.status === 'failure') return `${alias} 同步失败`
  if (log.status === 'partial_failure') return `${alias} 部分失败`
  if (log.status === 'partial_success') return `${alias} 部分完成`
  if (log.status === 'completed_with_skips') return `${alias} 完成但有跳过`
  if (log.status === 'already_running') return `${alias} 并发跳过`
  if (log.status === 'unknown') return `${alias} 状态未知`
  return `${alias} 执行中`
}

function getTimelineType(status: string): 'success' | 'warning' | 'error' | 'info' | 'default' {
  if (status === 'success') return 'success'
  if (status === 'failure') return 'error'
  if (status === 'partial_failure' || status === 'partial_success' || status === 'completed_with_skips') return 'warning'
  if (status === 'already_running') return 'info'
  if (status === 'unknown') return 'default'
  return 'info'
}
</script>

<style scoped>
.account-sync-overview {
  box-shadow: 0 8px 28px rgba(30, 64, 175, 0.04);
}
.account-sync-card {
  transition: border-color 180ms ease, transform 180ms ease, background-color 180ms ease;
}
.account-sync-card:hover {
  transform: translateY(-1px);
  border-color: rgba(59, 130, 246, 0.3);
}
.service-stat {
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.7);
}
.dark .service-stat {
  box-shadow: inset 0 0 0 1px rgba(51, 65, 85, 0.7);
}
.custom-scroll::-webkit-scrollbar {
  width: 4px;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background-color: #e2e8f0;
  border-radius: 4px;
}
.dark .custom-scroll::-webkit-scrollbar-thumb {
  background-color: #1f2937;
}
</style>
