<template>
  <div class="space-y-4 asset-shell">
        <!-- 头部视图 -->
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white/90 dark:bg-cardDark/90 border border-slate-200/80 dark:border-slate-700/70 px-4 py-3.5 rounded-lg shadow-sm">
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">云资产中心</h1>
              <span class="asset-count">{{ activeResourceCount }} 条</span>
            </div>
            <p class="mt-0.5 text-xs leading-4 text-slate-500 dark:text-slate-400 font-medium">
              {{ accountStore.activeAccount }} · {{ activeTab }} 资源
            </p>
          </div>

          <div class="flex items-center gap-2.5 mt-2 sm:mt-0">
            <n-input
              v-model:value="searchQuery"
              size="medium"
              placeholder="过滤表格..."
              clearable
              style="width: 180px"
              class="rounded-lg"
            >
              <template #prefix>
                <Icon icon="lucide:search" class="text-slate-400" />
              </template>
            </n-input>
            <n-popover trigger="click" placement="bottom-end" width="200">
              <template #trigger>
                <n-button size="medium" secondary>
                  <template #icon><Icon icon="lucide:sliders-horizontal" /></template>
                  自定义列
                </n-button>
              </template>
              <div class="p-2 space-y-2">
                <h4 class="font-bold text-xs text-slate-800 dark:text-slate-200 border-b border-borderLight dark:border-borderDark pb-1.5 mb-2">选择显示字段</h4>
                <n-checkbox-group v-model:value="resourceStore.visibleColumns[activeTab]" class="flex flex-col gap-2">
                  <n-checkbox v-for="col in allColumns[activeTab]" :key="col.value" :value="col.value">
                    {{ col.label }}
                  </n-checkbox>
                </n-checkbox-group>
              </div>
            </n-popover>
          </div>
        </div>

        <!-- 资源 Tabs 区 -->
        <section class="resource-panel bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl p-4">
          <!-- 错误状态 Alert -->
          <n-alert v-if="resourceStore.typeErrors[activeTab]" type="warning" title="数据实时更新失败" class="mb-4">
            {{ resourceStore.typeErrors[activeTab] }}（注：当前显示的可能为过期的本地缓存数据）
          </n-alert>
          <n-alert v-else-if="resourceStore.dbHealthState === 'unavailable'" type="error" title="数据库服务异常" class="mb-4">
            后台数据库连接或查询异常，资产数据暂时无法实时加载。
          </n-alert>

          <n-tabs v-model:value="activeTab" type="segment" size="medium" animated @update:value="onTabChange">
            <n-tab-pane name="ECS" tab="ECS 云服务器">
              <n-data-table
                class="resource-table"
                size="medium"
                :scroll-x="1420"
                :loading="resourceStore.loading"
                :columns="ecsColumns"
                :data="filteredEcs"
                :row-key="(row: any) => row.id"
                v-model:checked-row-keys="resourceStore.selectedRowKeys"
                :pagination="pagination"
                :striped="false"
              />
            </n-tab-pane>

            <n-tab-pane name="EIP" tab="弹性公网 IP">
              <n-data-table
                class="resource-table"
                size="medium"
                :scroll-x="900"
                :loading="resourceStore.loading"
                :columns="eipColumns"
                :data="filteredEip"
                :row-key="(row: any) => row.id"
                v-model:checked-row-keys="resourceStore.selectedRowKeys"
                :pagination="pagination"
                :striped="false"
              />
            </n-tab-pane>

            <n-tab-pane name="Domain" tab="域名资产">
              <n-data-table
                class="resource-table"
                size="medium"
                :scroll-x="820"
                :loading="resourceStore.loading"
                :columns="domainColumns"
                :data="filteredDomain"
                :row-key="(row: any) => row.id"
                v-model:checked-row-keys="resourceStore.selectedRowKeys"
                :pagination="pagination"
                :striped="false"
              />
            </n-tab-pane>

            <n-tab-pane name="SSL" tab="SSL 安全证书">
              <n-data-table
                class="resource-table"
                size="medium"
                :scroll-x="1080"
                :loading="resourceStore.loading"
                :columns="sslColumns"
                :data="filteredSsl"
                :row-key="(row: any) => row.id"
                v-model:checked-row-keys="resourceStore.selectedRowKeys"
                :pagination="pagination"
                :striped="false"
              />
            </n-tab-pane>
          </n-tabs>
        </section>

    <!-- 侧拉详情抽屉 -->
    <n-drawer v-model:show="resourceStore.isDetailDrawerOpen" :width="460" placement="right">
      <n-drawer-content title="资源详情控制台" closable>
        <DrawerEcs :record="resourceStore.activeDetailRow" />
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, h, onMounted, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { NButton, NTag } from 'naive-ui'
import { useRoute, useRouter } from 'vue-router'
import { useResourceStore, useAccountStore, useSettingStore } from '@/store'
import DrawerEcs from '@/components/DrawerEcs.vue'
import dayjs from 'dayjs'

const resourceStore = useResourceStore()
const accountStore = useAccountStore()
const settingStore = useSettingStore()
const route = useRoute()
const router = useRouter()

const activeTab = ref<'ECS' | 'EIP' | 'Domain' | 'SSL'>('ECS')
const searchQuery = ref('')

const filteredEcs = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return resourceStore.currentEcs
  return resourceStore.currentEcs.filter((row: any) => {
    const raw = (row.account_name || '') + ' ' + (row.search_key || '') + ' ' + JSON.stringify(row.details || {})
    return raw.toLowerCase().includes(q)
  })
})

const filteredEip = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return resourceStore.currentEip
  return resourceStore.currentEip.filter((row: any) => {
    const raw = (row.account_name || '') + ' ' + (row.search_key || '') + ' ' + JSON.stringify(row.details || {})
    return raw.toLowerCase().includes(q)
  })
})

const filteredDomain = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return resourceStore.currentDomain
  return resourceStore.currentDomain.filter((row: any) => {
    const raw = (row.account_name || '') + ' ' + (row.search_key || '') + ' ' + JSON.stringify(row.details || {})
    return raw.toLowerCase().includes(q)
  })
})

const filteredSsl = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return resourceStore.currentSsl
  return resourceStore.currentSsl.filter((row: any) => {
    const raw = (row.account_name || '') + ' ' + (row.search_key || '') + ' ' + JSON.stringify(row.details || {})
    return raw.toLowerCase().includes(q)
  })
})

const activeResourceCount = computed(() => ({
  ECS: filteredEcs.value.length,
  EIP: filteredEip.value.length,
  Domain: filteredDomain.value.length,
  SSL: filteredSsl.value.length,
}[activeTab.value]))

const accountOptions = computed(() => [
  { label: '全部账号', value: null },
  ...accountStore.accounts.map(account => ({
    label: account.account_alias,
    value: account.id,
  })),
])

// 监听路由参数以进行双向同步
watch(
  () => route.query.tab,
  (newTab) => {
    if (newTab && ['ECS', 'EIP', 'Domain', 'SSL'].includes(newTab as string)) {
      activeTab.value = newTab as 'ECS' | 'EIP' | 'Domain' | 'SSL'
    }
  },
  { immediate: true }
)

onMounted(async () => {
  await accountStore.loadAccounts()
  await resourceStore.loadAllResources()
})

function onTabChange(tab: string) {
  resourceStore.selectedRowKeys = []
  router.push({ query: { ...route.query, tab } })
}

async function onAccountFilter(accountId: number | null) {
  accountStore.activeAccountId = accountId
  accountStore.activeAccount = accountId === null
    ? '全部账号'
    : accountStore.accounts.find(account => account.id === accountId)?.account_alias || '全部账号'
  pagination.page = 1
  resourceStore.selectedRowKeys = []
  await resourceStore.loadAllResources(true)
}

const pagination = reactive({
  page: 1,
  pageSize: 15,
  showSizePicker: true,
  pageSizes: [15, 30, 50, 100],
  onChange: (page: number) => {
    pagination.page = page
  },
  onUpdatePageSize: (pageSize: number) => {
    pagination.pageSize = pageSize
    pagination.page = 1
  }
})

const allColumns = {
  ECS: [
    { label: '所属账号', value: 'account_name' },
    { label: '实例名称', value: 'instance_name' },
    { label: '实例 ID', value: 'instance_id' },
    { label: '区域', value: 'region_id' },
    { label: '实例状态', value: 'status' },
    { label: 'CPU 核数', value: 'cpu' },
    { label: '内存 (GB)', value: 'memory' },
    { label: '公网 IP', value: 'public_ips' },
    { label: '内网 IP', value: 'private_ips' },
    { label: '弹性 IP', value: 'eip' },
    { label: '释放到期', value: 'expired_time' },
  ],
  EIP: [
    { label: '所属账号', value: 'account_name' },
    { label: 'IP 地址', value: 'ip_address' },
    { label: '带宽 (Mbps)', value: 'bandwidth' },
    { label: '计费类型', value: 'charge_type' },
    { label: '关联实例', value: 'instance_id' },
    { label: '状态', value: 'status' },
    { label: '创建时间', value: 'creation_time' },
  ],
  Domain: [
    { label: '所属账号', value: 'account_name' },
    { label: '域名', value: 'domain_name' },
    { label: '注册日期', value: 'registration_date' },
    { label: '过期日期', value: 'expiration_date' },
    { label: '剩余天数', value: 'remaining_days' },
  ],
  SSL: [
    { label: '所属账号', value: 'account_name' },
    { label: '证书名称', value: 'cert_name' },
    { label: '关联域名', value: 'domain' },
    { label: '证书类型', value: 'cert_type' },
    { label: '证书品牌', value: 'brand' },
    { label: '生效时间', value: 'cert_start_time' },
    { label: '过期时间', value: 'cert_end_time' },
    { label: '剩余天数', value: 'remaining_days' },
    { label: '证书状态', value: 'status' },
  ],
}

const accountColumn: any = {
  title: '所属账号',
  key: 'account_name',
  width: 136,
  sorter: (a: any, b: any) => (a.account_name || '').localeCompare(b.account_name || ''),
  render(row: any) {
    return h('span', {
      class: 'inline-flex max-w-[124px] truncate rounded-md bg-slate-100 dark:bg-slate-800/80 px-2 py-0.5 text-[11px] font-medium text-slate-700 dark:text-slate-300',
      title: row.account_name || '-'
    }, row.account_name || '-')
  }
}

const ecsColumns = computed(() => {
  const visible = resourceStore.visibleColumns.ECS
  const list = [
    { type: 'selection' as const },
    accountColumn,
    {
      title: '实例名称',
      key: 'instance_name',
      sorter: (a: any, b: any) => (a.details?.instance_name || '').localeCompare(b.details?.instance_name || ''),
      render(row: any) {
        return h('span', { class: 'text-[11.5px] font-semibold text-slate-800 dark:text-slate-100' }, row.details.instance_name || '-')
      }
    },
    {
      title: '实例 ID',
      key: 'instance_id',
      sorter: (a: any, b: any) => (a.details?.instance_id || '').localeCompare(b.details?.instance_id || ''),
      render(row: any) { return h('span', { class: 'font-mono text-[11px] text-slate-400 dark:text-slate-500' }, row.details.instance_id) }
    },
    {
      title: '区域',
      key: 'region_id',
      sorter: (a: any, b: any) => (a.details?.region_id || '').localeCompare(b.details?.region_id || ''),
      render(row: any) { return h('span', { class: 'text-[11.5px] text-slate-700 dark:text-slate-300' }, row.details.region_id) }
    },
    {
      title: '实例状态',
      key: 'status',
      sorter: (a: any, b: any) => (a.details?.status || '').localeCompare(b.details?.status || ''),
      render(row: any) {
        const status = row.details.status
        let type: 'success' | 'warning' | 'error' | 'default' = 'default'
        let label = status
        if (status === 'Running') {
          type = 'success'
          label = '运行中'
        } else if (status === 'Stopped') {
          type = 'default'
          label = '已停止'
        } else {
          type = 'error'
          label = status || '异常'
        }
        return h(NTag, { size: 'small', type, bordered: false }, { default: () => label })
      }
    },
    { title: 'CPU', key: 'cpu', sorter: (a: any, b: any) => (a.details?.cpu || 0) - (b.details?.cpu || 0), render(row: any) { return h('span', { class: 'text-[11.5px] text-slate-700 dark:text-slate-300 font-medium' }, `${row.details.cpu}核`) } },
    {
      title: '内存',
      key: 'memory',
      sorter: (a: any, b: any) => (a.details?.memory || 0) - (b.details?.memory || 0),
      render(row: any) {
        const mem = row.details?.memory || 0
        if (!mem) return h('span', { class: 'text-[11.5px] text-slate-400' }, '-')
        if (mem < 1024) return h('span', { class: 'text-[11.5px] text-slate-700 dark:text-slate-300 font-medium' }, `${mem}MB`)
        const gb = mem / 1024
        return h('span', { class: 'text-[11.5px] text-slate-700 dark:text-slate-300 font-medium' }, `${gb % 1 === 0 ? gb.toFixed(0) : gb.toFixed(1)}G`)
      }
    },
    {
      title: '公网 IP',
      key: 'public_ips',
      render(row: any) {
        const ips = row.details.public_ips || []
        if (ips.length === 0) return h('span', { class: 'text-slate-400 dark:text-slate-500 text-[11px]' }, '-')
        return h('div', { class: 'flex flex-col gap-1' }, ips.map((ip: string) =>
          h('span', { class: 'text-[11px] font-mono px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400 font-medium whitespace-nowrap' }, ip)
        ))
      }
    },
    {
      title: '内网 IP',
      key: 'private_ips',
      render(row: any) {
        const ips = row.details.private_ips || []
        if (ips.length === 0) return h('span', { class: 'text-slate-400 dark:text-slate-500 text-[11px]' }, '-')
        return h('div', { class: 'flex flex-col gap-1' }, ips.map((ip: string) =>
          h('span', { class: 'text-[11px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-medium whitespace-nowrap' }, ip)
        ))
      }
    },
    {
      title: '弹性 IP',
      key: 'eip',
      render(row: any) {
        const eip = row.details.eip
        if (!eip) return h('span', { class: 'text-slate-400 dark:text-slate-500 text-[11px]' }, '-')
        return h('span', { class: 'text-[11px] font-mono px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-650 dark:text-purple-400 font-medium whitespace-nowrap' }, eip)
      }
    },
    {
      title: '释放到期',
      key: 'expired_time',
      sorter: (a: any, b: any) => {
        const ta = a.details?.expired_time ? dayjs(a.details.expired_time).valueOf() : 0
        const tb = b.details?.expired_time ? dayjs(b.details.expired_time).valueOf() : 0
        return ta - tb
      },
      render(row: any) { return h('span', { class: 'font-mono text-[11px] text-slate-600 dark:text-slate-300' }, row.details.expired_time?.replace('T', ' ').replace('Z', '') || '-') }
    },
    {
      title: '操作',
      key: 'action',
      render(row: any) {
        return h(NButton, {
          size: 'tiny',
          quaternary: true,
          type: 'primary',
          onClick: () => {
            resourceStore.activeDetailRow = row
            resourceStore.isDetailDrawerOpen = true
          }
        }, { default: () => '详情' })
      }
    }
  ]
  return list.filter(c => c.type === 'selection' || c.key === 'action' || visible.includes(c.key))
})

const eipColumns = computed(() => {
  const visible = resourceStore.visibleColumns.EIP
  const list = [
    { type: 'selection' as const },
    accountColumn,
    {
      title: 'IP 地址',
      key: 'ip_address',
      sorter: (a: any, b: any) => (a.details?.ip_address || '').localeCompare(b.details?.ip_address || ''),
      render(row: any) { return h('span', { class: 'font-mono text-[11.5px] font-semibold text-slate-800 dark:text-slate-100' }, row.details.ip_address) }
    },
    {
      title: '带宽 (Mbps)',
      key: 'bandwidth',
      sorter: (a: any, b: any) => (a.details?.bandwidth || 0) - (b.details?.bandwidth || 0),
      render(row: any) { return h('span', { class: 'text-[11.5px] text-slate-700 dark:text-slate-300 font-medium' }, `${row.details.bandwidth || '-'} Mbps`) }
    },
    { 
      title: '计费类型', 
      key: 'charge_type', 
      render(row: any) { 
        const ct = row.details.charge_type || row.details.internet_charge_type
        if (!ct) return h('span', { class: 'text-slate-400 dark:text-slate-500 text-[11.5px]' }, '未知')
        let label = ct
        if (ct === 'PayByTraffic') label = '按流量'
        else if (ct === 'PayByBandwidth') label = '按固定带宽'
        else if (ct === 'PrePaid') label = '包年包月'
        else if (ct === 'PostPaid') label = '按量付费'
        return h('span', { class: 'text-[11.5px] text-slate-700 dark:text-slate-300' }, label)
      } 
    },
    { title: '关联实例', key: 'instance_id', render(row: any) { return row.details.instance_id ? h('span', { class: 'font-mono text-[11px] text-slate-600 dark:text-slate-300' }, row.details.instance_id) : h('span', { class: 'text-slate-400 dark:text-slate-500 text-[11px]' }, '未绑定') } },
    {
      title: '状态',
      key: 'status',
      sorter: (a: any, b: any) => (a.details?.status || '').localeCompare(b.details?.status || ''),
      render(row: any) {
        const isAssigned = row.details.status === 'InUse'
        return h(NTag, { size: 'small', type: isAssigned ? 'success' : 'warning' }, { default: () => isAssigned ? '已绑定' : '闲置中' })
      }
    },
    {
      title: '创建时间',
      key: 'creation_time',
      sorter: (a: any, b: any) => {
        const ta = a.details?.allocation_time || a.details?.create_time || a.details?.creation_time || ''
        const tb = b.details?.allocation_time || b.details?.create_time || b.details?.creation_time || ''
        return ta.localeCompare(tb)
      },
      render(row: any) {
        const timeVal = row.details.allocation_time || row.details.create_time || row.details.creation_time
        return h('span', { class: 'font-mono text-[11px] text-slate-600 dark:text-slate-300' }, formatDate(timeVal))
      }
    }
  ]
  return list.filter(c => c.type === 'selection' || visible.includes(c.key))
})

const domainColumns = computed(() => {
  const visible = resourceStore.visibleColumns.Domain
  const list = [
    { type: 'selection' as const },
    accountColumn,
    {
      title: '域名',
      key: 'domain_name',
      sorter: (a: any, b: any) => {
        const da = a.details?.domain_name_unicode || a.details?.domain_name || ''
        const db = b.details?.domain_name_unicode || b.details?.domain_name || ''
        return da.localeCompare(db, 'zh-CN')
      },
      render(row: any) {
        const raw = row.details?.domain_name || ''
        const unicodeHint = row.details?.domain_name_unicode || ''
        const parsed = parseDomainUnicode(raw, unicodeHint)

        if (parsed.punycode && parsed.primary !== parsed.punycode) {
          return h('div', { class: 'flex flex-col justify-center py-0.5' }, [
            h('span', { class: 'font-bold text-slate-800 dark:text-slate-100 text-[11.5px] leading-tight' }, parsed.primary),
            h('span', { class: 'font-mono text-[10.5px] text-slate-400 dark:text-slate-500 font-medium' }, parsed.punycode)
          ])
        }

        return h('span', { class: 'font-semibold text-slate-800 dark:text-slate-100 text-[11.5px]' }, parsed.primary)
      }
    },
    {
      title: '注册日期',
      key: 'registration_date',
      sorter: (a: any, b: any) => (a.details?.registration_date || '').localeCompare(b.details?.registration_date || ''),
      render(row: any) { return h('span', { class: 'font-mono text-[11px] text-slate-600 dark:text-slate-300' }, row.details.registration_date || '-') }
    },
    {
      title: '过期日期',
      key: 'expiration_date',
      sorter: (a: any, b: any) => (a.details?.expiration_date || '').localeCompare(b.details?.expiration_date || ''),
      render(row: any) { return h('span', { class: 'font-mono text-[11px] text-slate-600 dark:text-slate-300' }, row.details.expiration_date || '-') }
    },
    {
      title: '剩余天数',
      key: 'remaining_days',
      sorter: (a: any, b: any) => {
        const da = a.details?.expiration_date ? dayjs(a.details.expiration_date).startOf('day').diff(dayjs().startOf('day'), 'day') : 99999
        const db = b.details?.expiration_date ? dayjs(b.details.expiration_date).startOf('day').diff(dayjs().startOf('day'), 'day') : 99999
        return da - db
      },
      render(row: any) {
        const expDate = row.details.expiration_date
        if (!expDate) return h('span', { class: 'text-slate-400 text-[11px]' }, '-')
        const days = dayjs(expDate).startOf('day').diff(dayjs().startOf('day'), 'day')
        let type: 'success' | 'warning' | 'error' | 'info' = 'success'
        if (days <= settingStore.criticalDays) {
          type = 'error'
        } else if (days <= settingStore.warningDays) {
          type = 'warning'
        } else if (days <= settingStore.reminderDays) {
          type = 'info'
        }
        return h(NTag, { size: 'small', type }, { default: () => days < 0 ? '已过期' : `${days}天` })
      }
    }
  ]
  return list.filter(c => c.type === 'selection' || visible.includes(c.key))
})

const sslColumns = computed(() => {
  const visible = resourceStore.visibleColumns.SSL
  const list = [
    { type: 'selection' as const },
    accountColumn,
    {
      title: '证书名称',
      key: 'cert_name',
      sorter: (a: any, b: any) => (a.details?.cert_name || '').localeCompare(b.details?.cert_name || ''),
      render(row: any) { return h('span', { class: 'font-semibold text-slate-800 dark:text-slate-100 text-[11.5px]' }, row.details.cert_name || '-') }
    },
    {
      title: '关联域名',
      key: 'domain',
      sorter: (a: any, b: any) => (a.details?.domain || '').localeCompare(b.details?.domain || ''),
      render(row: any) { return h('span', { class: 'text-[11.5px] text-slate-700 dark:text-slate-300' }, row.details.domain || '-') }
    },
    {
      title: '证书类型',
      key: 'cert_type',
      sorter: (a: any, b: any) => (a.details?.cert_type || '').localeCompare(b.details?.cert_type || ''),
      render(row: any) {
        const type = row.details.cert_type || 'DV'
        let bgClass = 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-350'
        if (type.toLowerCase().includes('free') || type.includes('免费')) {
          bgClass = 'bg-teal-500/10 text-teal-600 dark:text-teal-400'
        } else if (type.toUpperCase().includes('EV')) {
          bgClass = 'bg-indigo-500/10 text-indigo-600 dark:text-indigo-400'
        } else if (type.toUpperCase().includes('OV')) {
          bgClass = 'bg-blue-500/10 text-blue-600 dark:text-blue-400 font-bold'
        }
        return h('span', { class: `text-[11px] px-2 py-0.5 rounded font-semibold ${bgClass} whitespace-nowrap` }, type)
      }
    },
    {
      title: '证书品牌',
      key: 'brand',
      sorter: (a: any, b: any) => (a.details?.brand || '').localeCompare(b.details?.brand || ''),
      render(row: any) { return h('span', { class: 'text-[11.5px] text-slate-600 dark:text-slate-400' }, row.details.brand || '-') }
    },
    {
      title: '生效时间',
      key: 'cert_start_time',
      sorter: (a: any, b: any) => (a.details?.cert_start_time || '').localeCompare(b.details?.cert_start_time || ''),
      render(row: any) { return h('span', { class: 'font-mono text-[11px] text-slate-600 dark:text-slate-300' }, row.details.cert_start_time || '-') }
    },
    {
      title: '到期时间',
      key: 'cert_end_time',
      sorter: (a: any, b: any) => (a.details?.cert_end_time || '').localeCompare(b.details?.cert_end_time || ''),
      render(row: any) { return h('span', { class: 'font-mono text-[11px] text-slate-600 dark:text-slate-300' }, row.details.cert_end_time || '-') }
    },
    {
      title: '剩余天数',
      key: 'remaining_days',
      sorter: (a: any, b: any) => {
        const da = a.details?.cert_end_time ? dayjs(a.details.cert_end_time).startOf('day').diff(dayjs().startOf('day'), 'day') : 99999
        const db = b.details?.cert_end_time ? dayjs(b.details.cert_end_time).startOf('day').diff(dayjs().startOf('day'), 'day') : 99999
        return da - db
      },
      render(row: any) {
        const expDate = row.details.cert_end_time
        if (!expDate) return h('span', { class: 'text-slate-400 text-[11px]' }, '-')
        const days = dayjs(expDate).startOf('day').diff(dayjs().startOf('day'), 'day')
        const threshold = settingStore.warningDaysThreshold
        let type: 'success' | 'warning' | 'error' = 'success'
        if (days < 0) {
          type = 'error'
        } else if (days <= threshold) {
          type = 'warning'
        }
        return h(NTag, { size: 'small', type }, { default: () => days < 0 ? '已过期' : `${days}天` })
      }
    },
    {
      title: '证书状态',
      key: 'status',
      render(row: any) {
        const expDate = row.details.cert_end_time
        if (!expDate) return h('span', { class: 'text-slate-400 text-[11px]' }, '-')
        const days = dayjs(expDate).startOf('day').diff(dayjs().startOf('day'), 'day')
        const threshold = settingStore.warningDaysThreshold
        let label = '正常'
        let type: 'success' | 'warning' | 'error' = 'success'
        if (days < 0) {
          label = '已过期'
          type = 'error'
        } else if (days <= threshold) {
          label = '即将过期'
          type = 'warning'
        }
        return h(NTag, { size: 'small', type }, { default: () => label })
      }
    }
  ]
  return list.filter(c => c.type === 'selection' || visible.includes(c.key))
})

function decodePunycodePart(input: string): string {
  if (!input.toLowerCase().startsWith('xn--')) return input
  const pubStr = input.slice(4)
  const BASE = 36, TMIN = 1, TMAX = 26, SKEW = 38, DAMP = 700, INITIAL_BIAS = 72, INITIAL_N = 128
  let n = INITIAL_N, i = 0, bias = INITIAL_BIAS
  const output: number[] = []
  
  const delim = pubStr.lastIndexOf('-')
  let basic = 0
  if (delim > 0) {
    for (let j = 0; j < delim; ++j) {
      output.push(pubStr.charCodeAt(j))
    }
    basic = delim + 1
  }
  
  let inLen = pubStr.length
  for (let k = basic; k < inLen;) {
    let oldi = i, w = 1, k1 = BASE
    while (true) {
      if (k >= inLen) return input
      let digit = pubStr.charCodeAt(k++)
      digit = digit - 48 < 10 ? digit - 22 : digit - 65 < 26 ? digit - 65 : digit - 97 < 26 ? digit - 97 : BASE
      if (digit >= BASE) return input
      if (digit > Math.floor((2147483647 - i) / w)) return input
      i += digit * w
      let t = k1 <= bias ? TMIN : k1 >= bias + TMAX ? TMAX : k1 - bias
      if (digit < t) break
      if (w > Math.floor(2147483647 / (BASE - t))) return input
      w *= (BASE - t)
      k1 += BASE
    }
    let outLen = output.length + 1
    let delta = k1 === BASE ? Math.floor(i / DAMP) : Math.floor((i - oldi) / 2)
    delta += Math.floor(delta / outLen)
    let k2 = 0
    while (delta > Math.floor(((BASE - TMIN) * TMAX) / 2)) {
      delta = Math.floor(delta / (BASE - TMIN))
      k2 += BASE
    }
    bias = Math.floor(k2 + (((BASE - TMIN + 1) * delta) / (delta + SKEW)))
    if (Math.floor(i / outLen) > 2147483647 - n) return input
    n += Math.floor(i / outLen)
    i %= outLen
    output.splice(i++, 0, n)
  }
  return String.fromCodePoint(...output)
}

function parseDomainUnicode(domainStr?: string, unicodeFallback?: string): { primary: string, punycode?: string } {
  if (!domainStr) return { primary: '-' }
  const raw = domainStr.trim()
  let unicodeName = unicodeFallback || ''
  
  if (!unicodeName) {
    if (raw.toLowerCase().includes('xn--')) {
      try {
        unicodeName = raw.split('.').map(decodePunycodePart).join('.')
      } catch (e) {
        unicodeName = raw
      }
    } else {
      unicodeName = raw
    }
  }
  
  if (raw.toLowerCase().includes('xn--') || (unicodeName && unicodeName !== raw)) {
    return {
      primary: unicodeName,
      punycode: raw.toLowerCase().includes('xn--') ? raw : undefined
    }
  }
  return { primary: raw }
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '-'
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
  } catch (e) {
    return dateStr
  }
}
</script>

<style scoped>
.asset-shell {
  background:
    radial-gradient(circle at 88% 0%, rgba(22, 119, 255, 0.045), transparent 28rem),
    transparent;
}

.asset-count {
  padding: 2px 7px;
  border-radius: 5px;
  background: #eff6ff;
  color: #2563eb;
  font-size: 10px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.resource-panel {
  box-shadow: 0 8px 28px rgba(30, 64, 175, 0.045);
}

.resource-table {
  font-variant-numeric: tabular-nums;
}

/* ── 浅色主题下的表格样式（默认，无需 html:not(.dark) 选择器） ── */
.resource-table :deep(.n-data-table-th) {
  height: 38px;
  padding: 8px 14px;
  background: #ffffff !important;
  color: #475569;
  font-size: 13px !important;
  font-weight: 600;
  letter-spacing: 0.01em;
  border-bottom: 1.5px solid #e2e8f0;
  transition: color 0.2s ease;
}

.resource-table :deep(.n-data-table-th--sortable:hover) {
  background: #ffffff !important;
  color: #2563eb !important;
}

.resource-table :deep(.n-data-table-th--sort-active) {
  background: #ffffff !important;
  color: #2563eb !important;
  font-weight: 700;
}

.resource-table :deep(.n-data-table-th--sort-active .n-data-table-sorter) {
  color: #2563eb !important;
}

.resource-table :deep(.n-data-table-td) {
  height: 44px;
  padding: 9px 14px;
  background: #ffffff !important;
  color: #334155;
  font-size: 13px !important;
  line-height: 1.45;
  border-bottom: 1px solid #f1f5f9;
  transition: background-color 0.18s ease;
}

.resource-table :deep(.n-data-table-tr:hover .n-data-table-td) {
  background: #f8fafc !important;
}

.resource-table :deep(.n-data-table-sorter) {
  margin-left: 4px;
  color: #94a3b8;
  transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1), color 0.2s ease;
}

.resource-table :deep(.n-data-table-tr) {
  transition: background-color 0.18s ease;
}

.resource-table :deep(.n-tag) {
  height: 24px;
  padding: 0 8px;
  border-radius: 6px;
  font-size: 12px !important;
  font-weight: 500;
  transition: all 0.2s ease;
}

.resource-panel :deep(.n-tabs-tab) {
  min-height: 34px;
  font-size: 13px !important;
  font-weight: 600;
}

.resource-panel :deep(.n-pagination) {
  font-size: 12px;
}

/* ── 深色主题下的表格样式（用 :global(.dark) 匹配 html 上的 .dark 类） ── */
:global(.dark) .asset-count {
  background: rgba(37, 99, 235, 0.16);
  color: #93c5fd;
}

:global(.dark) .resource-panel {
  box-shadow: 0 10px 32px rgba(2, 6, 23, 0.24);
}

:global(.dark) .resource-table :deep(.n-data-table-th) {
  height: 38px;
  padding: 8px 14px;
  background: #111827 !important;
  color: #94a3b8 !important;
  font-size: 13px !important;
  font-weight: 600;
  letter-spacing: 0.01em;
  border-bottom: 1.5px solid rgba(51, 65, 85, 0.6) !important;
}

:global(.dark) .resource-table :deep(.n-data-table-th--sortable:hover) {
  background: #111827 !important;
  color: #60a5fa !important;
}

:global(.dark) .resource-table :deep(.n-data-table-th--sort-active) {
  background: #111827 !important;
  color: #60a5fa !important;
  font-weight: 700;
}

:global(.dark) .resource-table :deep(.n-data-table-th--sort-active .n-data-table-sorter) {
  color: #60a5fa !important;
}

:global(.dark) .resource-table :deep(.n-data-table-td) {
  height: 44px;
  padding: 9px 14px;
  background: #111827 !important;
  color: #cbd5e1 !important;
  font-size: 13px !important;
  line-height: 1.45;
  border-bottom: 1px solid rgba(51, 65, 85, 0.35) !important;
}

:global(.dark) .resource-table :deep(.n-data-table-tr:hover .n-data-table-td) {
  background: #1f2937 !important;
}
</style>
