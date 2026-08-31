<template>
  <div class="space-y-4">
    <!-- 头部欢迎语与全局进度状态 -->
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white/90 dark:bg-cardDark/90 border border-slate-200/80 dark:border-slate-700/70 px-4 py-3.5 rounded-lg shadow-sm">
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-base font-semibold tracking-tight text-slate-900 dark:text-slate-100">云资产监控中心</h1>
            </div>
            <p class="mt-0.5 text-[13px] leading-5 text-slate-500 dark:text-slate-400 font-normal">
              您当前已绑定了 {{ accountStore.accounts.length }} 个云账号，当前过滤视图：{{ accountStore.activeAccount }}。
            </p>
          </div>
          
          <!-- 同步进度提示 (如果有任务在运行) -->
          <div v-if="syncStore.syncing" class="flex items-center gap-3 bg-primary/10 border border-primary/20 px-4 py-2.5 rounded-xl">
            <Icon icon="lucide:refresh-cw" class="animate-spin text-primary" :width="16" />
            <span class="text-xs text-primary font-medium font-mono">资产刷新中... 已耗时 {{ syncStore.syncTimeElapsed }} 秒</span>
            <n-button size="tiny" quaternary type="error" @click="syncStore.stopTracking()">停止跟踪</n-button>
          </div>
        </div>

        <!-- 指标统计卡片 -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 dash-stagger">
          <StatCard title="云服务器 ECS" :value="resourceStore.ecsList.length" icon="lucide:server" iconColor="text-primary" />
          <StatCard title="弹性公网 IP" :value="resourceStore.eipList.length" icon="lucide:globe" iconColor="text-indigo-500" />
          <StatCard title="域名资产" :value="resourceStore.domainList.length" icon="lucide:link-2" iconColor="text-success" />
          <StatCard title="SSL 证书" :value="resourceStore.sslList.length" icon="lucide:shield-check" iconColor="text-amber-500" />
          <StatCard title="API 调用 (近7天)" :value="resourceStore.apiCallStats.week_total" icon="lucide:activity" iconColor="text-sky-500" />
        </div>

        <!-- 阿里云 API 调用请求监控统计面板 -->
        <section class="bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl p-5 shadow-sm">
          <div class="flex items-center justify-between mb-4">
            <div>
              <h3 class="text-[14px] font-medium text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <Icon icon="lucide:activity" :width="16" class="text-sky-500" />
                阿里云 API 请求监控统计
              </h3>
              <p class="mt-1 text-xs text-slate-400 dark:text-slate-500">自动记录后台同步任务发起阿里云 OpenAPI/SDK 请求调用的近 7 天分布与趋势</p>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
            <!-- 统计概览 1: 近一周 -->
            <div class="rounded-lg border border-slate-200/80 dark:border-slate-700/70 bg-gradient-to-br from-blue-50/50 to-indigo-50/30 dark:from-slate-900/40 dark:to-slate-900/20 p-4">
              <div class="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs font-normal">
                <span>近一周总调用量 (7天)</span>
                <Icon icon="lucide:calendar-range" :width="16" class="text-blue-500" />
              </div>
              <div class="mt-2 text-2xl font-semibold tracking-tight text-slate-800 dark:text-slate-100 font-mono">
                {{ resourceStore.apiCallStats.week_total.toLocaleString() }} <span class="text-xs font-normal text-slate-500">次</span>
              </div>
              <div class="mt-1 text-xs text-slate-500 dark:text-slate-400">
                阿里云 SDK/OpenAPI 请求累计触发
              </div>
            </div>

            <!-- 统计概览 2: 今日 vs 昨日 -->
            <div class="rounded-lg border border-slate-200/80 dark:border-slate-700/70 bg-gradient-to-br from-emerald-50/50 to-teal-50/30 dark:from-slate-900/40 dark:to-slate-900/20 p-4 flex flex-col justify-between">
              <div class="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs font-normal">
                <span>今日 / 昨日对比</span>
                <Icon icon="lucide:clock" :width="16" class="text-emerald-500" />
              </div>
              <div class="mt-2 grid grid-cols-2 gap-2">
                <div class="bg-white/80 dark:bg-slate-800/60 rounded-lg p-2 border border-emerald-500/15">
                  <div class="text-[11px] text-slate-400 font-normal">今日调用</div>
                  <div class="text-xl font-semibold text-emerald-600 dark:text-emerald-400 font-mono mt-0.5">
                    {{ resourceStore.apiCallStats.today_total.toLocaleString() }} <span class="text-[10px] font-normal text-slate-400">次</span>
                  </div>
                </div>
                <div class="bg-white/80 dark:bg-slate-800/60 rounded-lg p-2 border border-slate-200/60 dark:border-slate-700/50">
                  <div class="text-[11px] text-slate-400 font-normal">昨日全天</div>
                  <div class="text-xl font-semibold text-slate-600 dark:text-slate-300 font-mono mt-0.5">
                    {{ resourceStore.apiCallStats.yesterday_total.toLocaleString() }} <span class="text-[10px] font-normal text-slate-400">次</span>
                  </div>
                </div>
              </div>
              <div class="mt-2 text-xs text-slate-500 dark:text-slate-400">
                今日 0:00 至今新增请求
              </div>
            </div>

            <!-- 统计概览 3: 按服务分类分布 -->
            <div class="rounded-lg border border-slate-200/80 dark:border-slate-700/70 bg-slate-50/70 dark:bg-slate-900/35 p-3.5 flex flex-col justify-between">
              <div class="text-xs font-normal text-slate-600 dark:text-slate-300 mb-2">按服务分类调用占比</div>
              <div class="space-y-2">
                <div v-for="(val, sKey) in resourceStore.apiCallStats.by_service" :key="sKey" class="flex items-center justify-between text-xs">
                  <span class="text-slate-500 dark:text-slate-400 font-normal">{{ getServiceName(sKey) }}</span>
                  <div class="flex items-center gap-2">
                    <div class="w-24 bg-slate-200 dark:bg-slate-700 rounded-full h-1.5 overflow-hidden">
                      <div
                        class="h-full rounded-full transition-all duration-500"
                        :class="getServiceBarColor(sKey)"
                        :style="{ width: getServicePercent(val) + '%' }"
                      ></div>
                    </div>
                    <span class="font-mono text-slate-700 dark:text-slate-300 w-12 text-right">{{ val }}次</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 各云账号独立 API 调用明细 -->
          <div v-if="resourceStore.apiCallStats.by_account && resourceStore.apiCallStats.by_account.length" class="mt-4 pt-3.5 border-t border-slate-200/70 dark:border-slate-700/60">
            <div class="text-[13px] font-medium text-slate-700 dark:text-slate-200 mb-2.5 flex items-center justify-between">
              <span class="flex items-center gap-1.5">
                <Icon icon="lucide:users" :width="14" class="text-indigo-500" />
                各云账号 API 请求明细
              </span>
              <span class="text-xs text-slate-400 font-normal">统计近 7 天各账号产生的 OpenAPI 请求总量与今日调用</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4 gap-3">
              <div
                v-for="accStat in resourceStore.apiCallStats.by_account"
                :key="accStat.account_id"
                class="rounded-lg border border-slate-200/70 dark:border-slate-700/60 bg-white/70 dark:bg-slate-900/40 p-3 flex flex-col justify-between shadow-[0_1px_2px_rgba(0,0,0,0.02)] transition-transform duration-160 hover:-translate-y-0.5 hover:shadow-md"
              >
                <div class="flex items-center justify-between gap-2">
                  <span class="font-medium text-[13px] text-slate-800 dark:text-slate-100 truncate" :title="accStat.account_alias">
                    {{ accStat.account_alias }}
                  </span>
                  <span class="font-mono text-xs font-normal text-primary tabular-nums">
                    {{ accStat.week_total }} <span class="text-[11px] font-normal text-slate-400">次/周</span>
                  </span>
                </div>

                <div class="mt-2 text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between">
                  <span>今日: <span class="font-mono font-medium text-emerald-600 dark:text-emerald-400">{{ accStat.today_total }}</span> 次</span>
                  <span>昨日: <span class="font-mono font-medium text-slate-600 dark:text-slate-300">{{ accStat.yesterday_total }}</span> 次</span>
                </div>

                <div class="mt-2.5 pt-2 border-t border-slate-200/50 dark:border-slate-700/40 grid grid-cols-4 gap-1 text-[11px] text-center font-mono">
                  <div class="bg-slate-50 dark:bg-slate-800/60 border border-slate-200/50 dark:border-slate-700/40 rounded px-1 py-1" title="ECS API 请求数">
                    <span class="text-slate-400 block text-[10px]">ECS</span>
                    <span :class="accStat.by_service.ECS > 0 ? 'text-blue-600 dark:text-blue-400 font-medium' : 'text-slate-400 font-normal'">{{ accStat.by_service.ECS }}</span>
                  </div>
                  <div class="bg-slate-50 dark:bg-slate-800/60 border border-slate-200/50 dark:border-slate-700/40 rounded px-1 py-1" title="EIP API 请求数">
                    <span class="text-slate-400 block text-[10px]">EIP</span>
                    <span :class="accStat.by_service.EIP > 0 ? 'text-indigo-600 dark:text-indigo-400 font-medium' : 'text-slate-400 font-normal'">{{ accStat.by_service.EIP }}</span>
                  </div>
                  <div class="bg-slate-50 dark:bg-slate-800/60 border border-slate-200/50 dark:border-slate-700/40 rounded px-1 py-1" title="Domain API 请求数">
                    <span class="text-slate-400 block text-[10px]">域名</span>
                    <span :class="accStat.by_service.Domain > 0 ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-slate-400 font-normal'">{{ accStat.by_service.Domain }}</span>
                  </div>
                  <div class="bg-slate-50 dark:bg-slate-800/60 border border-slate-200/50 dark:border-slate-700/40 rounded px-1 py-1" title="SSL API 请求数">
                    <span class="text-slate-400 block text-[10px]">SSL</span>
                    <span :class="accStat.by_service.SSL > 0 ? 'text-amber-600 dark:text-amber-400 font-medium' : 'text-slate-400 font-normal'">{{ accStat.by_service.SSL }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="account-sync-overview bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl p-5 shadow-sm">
          <div class="flex items-start justify-between gap-4 mb-4">
            <div>
              <h3 class="text-[14px] font-medium text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <Icon icon="lucide:database-zap" :width="15" class="text-primary" />
                云账号资源同步概览
              </h3>
              <p class="mt-1 text-xs text-slate-400 dark:text-slate-500">按账号展示最近一次 ECS、EIP、域名和 SSL 同步结果</p>
            </div>
            <span class="text-xs font-normal text-slate-400 dark:text-slate-500">{{ accountStore.accounts.length }} 个账号</span>
          </div>

          <div v-if="accountStore.accounts.length" class="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-4 gap-3.5">
            <article
              v-for="account in accountStore.accounts"
              :key="`sync-overview-${account.id}`"
              class="account-sync-card rounded-xl border border-slate-200/80 dark:border-slate-700/70 bg-gradient-to-b from-white to-slate-50/70 dark:from-slate-900/60 dark:to-slate-900/30 p-4 shadow-[0_1px_3px_rgba(0,0,0,0.03)] hover:shadow-md transition-all duration-200"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <h4 class="truncate text-[13px] font-medium text-slate-800 dark:text-slate-100" :title="account.account_alias">{{ account.account_alias }}</h4>
                  <p class="mt-0.5 text-xs text-slate-400 dark:text-slate-500">成功同步 {{ getAccountResourceTotal(account) }} 项资源</p>
                </div>
                <!-- 呼吸指示灯风格胶囊 -->
                <div
                  class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-normal border"
                  :class="getAccountSyncBadgeClass(account.last_sync_status)"
                >
                  <span class="w-1.5 h-1.5 rounded-full mr-1.5" :class="getAccountSyncDotClass(account.last_sync_status)"></span>
                  {{ getAccountSyncLabel(account.last_sync_status) }}
                </div>
              </div>

              <div class="mt-3.5 grid grid-cols-4 gap-1.5">
                <div
                  v-for="service in syncServices"
                  :key="service.key"
                  class="service-stat rounded-lg bg-white dark:bg-slate-800/80 border border-slate-200/70 dark:border-slate-700/60 px-1.5 py-2 text-center shadow-[0_1px_2px_rgba(0,0,0,0.02)] transition-colors"
                  :title="getServiceError(account, service.key)"
                >
                  <div class="text-[11px] font-normal text-slate-400 dark:text-slate-500">{{ service.label }}</div>
                  <div class="mt-1 text-[13px] font-medium tabular-nums" :class="getServiceValueClass(account, service.key)">
                    {{ getServiceValue(account, service.key) }}
                  </div>
                </div>
              </div>

              <div class="mt-3 pt-2.5 border-t border-slate-200/60 dark:border-slate-700/50">
                <div class="flex items-center justify-between mb-1.5">
                  <span class="text-xs font-normal text-slate-400 dark:text-slate-500 flex items-center gap-1">
                    <Icon icon="lucide:map-pin" :width="12" class="text-sky-500" />
                    活跃同步地域 ({{ (account.active_regions || []).length }}个)
                  </span>
                </div>
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="reg in (account.active_regions || [])"
                    :key="reg"
                    class="inline-flex items-center px-2 py-0.5 rounded-full bg-sky-500/10 dark:bg-sky-500/15 text-sky-600 dark:text-sky-400 border border-sky-500/20 text-[10.5px] font-normal font-mono leading-none"
                  >
                    {{ getRegionName(reg) }}
                  </span>
                  <span v-if="!account.active_regions || account.active_regions.length === 0" class="text-xs text-slate-400">默认主地域</span>
                </div>
              </div>

              <div class="mt-3 flex items-center justify-between border-t border-slate-200/70 dark:border-slate-700/60 pt-2.5 text-xs text-slate-400 dark:text-slate-500">
                <span>最近成功</span>
                <span class="font-mono tabular-nums">{{ formatSyncTime(account.last_synced_at) }}</span>
              </div>
            </article>
          </div>
          <div v-else class="py-8 text-center text-xs text-slate-400">暂无云账号</div>
        </section>

        <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 shadow-sm">
          <h3 class="text-[14px] font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1.5 mb-4">
            <Icon icon="lucide:cloud-cog" :width="15" />
            云账号最近同步情况
          </h3>
          <div class="overflow-x-auto">
            <table class="w-full text-[13px]">
              <thead class="text-left text-slate-400 border-b border-borderLight dark:border-borderDark text-xs">
                <tr>
                  <th class="py-2.5 pr-4 font-medium">云账号</th>
                  <th class="py-2.5 pr-4 font-medium">最近状态</th>
                  <th class="py-2.5 pr-4 font-medium">活跃同步地域</th>
                  <th class="py-2.5 pr-4 font-medium">最近尝试</th>
                  <th class="py-2.5 pr-4 font-medium">最近成功</th>
                  <th class="py-2.5 font-medium">结果摘要</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="account in accountStore.accounts" :key="account.id" class="border-b last:border-0 border-borderLight dark:border-borderDark">
                  <td class="py-3 pr-4 font-normal text-slate-800 dark:text-slate-200">{{ account.account_alias }}</td>
                  <td class="py-3 pr-4">
                    <div
                      class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-normal border"
                      :class="getAccountSyncBadgeClass(account.last_sync_status)"
                    >
                      <span class="w-1.5 h-1.5 rounded-full mr-1.5" :class="getAccountSyncDotClass(account.last_sync_status)"></span>
                      {{ getAccountSyncLabel(account.last_sync_status) }}
                    </div>
                  </td>
                  <td class="py-3 pr-4">
                    <div class="flex flex-wrap gap-1 max-w-[260px]">
                      <span
                        v-for="reg in (account.active_regions || [])"
                        :key="reg"
                        class="inline-flex items-center px-2 py-0.5 rounded-full bg-sky-500/10 dark:bg-sky-500/15 text-sky-600 dark:text-sky-400 border border-sky-500/20 text-[10.5px] font-normal font-mono leading-none"
                      >
                        {{ getRegionName(reg) }}
                      </span>
                    </div>
                  </td>
                  <td class="py-3 pr-4 whitespace-nowrap font-mono text-xs text-slate-600 dark:text-slate-300">{{ formatSyncTime(account.last_attempted_at) }}</td>
                  <td class="py-3 pr-4 whitespace-nowrap font-mono text-xs text-slate-600 dark:text-slate-300">{{ formatSyncTime(account.last_synced_at) }}</td>
                  <td class="py-3 max-w-[420px] truncate font-normal text-slate-600 dark:text-slate-300" :title="getFormattedSyncSummary(account)">
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
                <h3 class="text-[14px] font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1.5 mb-4">
                  <Icon icon="lucide:pie-chart" :width="15" />
                  资产类型分布比例
                </h3>
                <div class="flex-grow flex items-center justify-center">
                  <EchartsPie :data="pieData" title="资产占比" />
                </div>
              </div>

              <!-- 到期警报卡片 -->
              <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 flex flex-col justify-between shadow-sm">
                <h3 class="text-[14px] font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1.5 mb-4">
                  <Icon icon="lucide:alert-triangle" :width="15" class="text-amber-550 dark:text-warning" />
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
                        <div class="text-[13px] font-normal text-slate-800 dark:text-slate-200">{{ d.details.domain_name }}</div>
                        <div class="text-xs text-slate-400 dark:text-slate-500 mt-1 font-mono">过期日: {{ d.details.expiration_date }}</div>
                      </div>
                      <n-tag size="small" :type="getAlertLevel(d.details.expiration_date)">{{ getRemainingDaysText(d.details.expiration_date) }}</n-tag>
                    </div>

                    <!-- 到期证书 -->
                    <div v-for="c in notificationStore.warningCerts" :key="c.id" class="p-3 bg-slate-50 dark:bg-slate-900/50 border border-borderLight dark:border-borderDark rounded-lg flex items-center justify-between hover:border-amber-500/20 transition duration-200">
                      <div>
                        <div class="text-[13px] font-normal text-slate-800 dark:text-slate-200">{{ c.details.cert_name }}</div>
                        <div class="text-xs text-slate-400 dark:text-slate-500 mt-1 font-mono">过期日: {{ c.details.cert_end_time }}</div>
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
            <h3 class="text-[14px] font-medium text-slate-700 dark:text-slate-300 flex items-center gap-1.5 mb-6">
              <Icon icon="lucide:history" :width="15" />
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

function getAccountSyncBadgeClass(status?: string): string {
  if (status === 'success') return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
  if (status === 'partial_failure') return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
  if (status === 'failure') return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
  return 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400 border-slate-200 dark:border-slate-700'
}

function getAccountSyncDotClass(status?: string): string {
  if (status === 'success') return 'bg-emerald-500 animate-pulse'
  if (status === 'partial_failure') return 'bg-amber-500'
  if (status === 'failure') return 'bg-rose-500'
  return 'bg-slate-400'
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

function getServiceName(key: string | number): string {
  const map: Record<string, string> = {
    ECS: '云服务器 ECS',
    EIP: '弹性公网 IP',
    Domain: '域名资产',
    SSL: 'SSL 证书'
  }
  return map[String(key)] || String(key)
}

function getServiceBarColor(key: string | number): string {
  const map: Record<string, string> = {
    ECS: 'bg-blue-500',
    EIP: 'bg-indigo-500',
    Domain: 'bg-emerald-500',
    SSL: 'bg-amber-500'
  }
  return map[String(key)] || 'bg-blue-500'
}

function getServicePercent(val: number): number {
  const total = resourceStore.apiCallStats.week_total || 1
  return Math.min(100, Math.round((val / total) * 100))
}
</script>

<style scoped>
.account-sync-overview {
  box-shadow: 0 8px 28px rgba(30, 64, 175, 0.04);
}

/* 顶部指标卡片错峰级联进入 (Stagger) */
.dash-stagger > * {
  animation: fadeUp 240ms cubic-bezier(0.23, 1, 0.32, 1) backwards;
}
.dash-stagger > *:nth-child(1) { animation-delay: 0ms; }
.dash-stagger > *:nth-child(2) { animation-delay: 35ms; }
.dash-stagger > *:nth-child(3) { animation-delay: 70ms; }
.dash-stagger > *:nth-child(4) { animation-delay: 105ms; }
.dash-stagger > *:nth-child(5) { animation-delay: 140ms; }

.account-sync-card {
  transition: border-color 160ms ease, transform 160ms cubic-bezier(0.23, 1, 0.32, 1), background-color 160ms ease;
}

@media (hover: hover) and (pointer: fine) {
  .account-sync-card:hover {
    transform: translateY(-1.5px);
    border-color: rgba(59, 130, 246, 0.35);
  }
}

.service-stat {
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.7);
  transition: background-color 160ms ease;
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
