<template>
  <div class="space-y-4">
        <!-- 头部标题 -->
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white/90 dark:bg-cardDark/90 border border-slate-200/80 dark:border-slate-700/70 px-4 py-3.5 rounded-lg shadow-sm">
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">云凭证管理</h1>
            </div>
            <p class="mt-0.5 text-xs leading-4 text-slate-500 dark:text-slate-400 font-medium">
              配置多阿里云 RAM 账户，拉取云资产
            </p>
          </div>
          <n-button type="primary" size="medium" class="mt-2 sm:mt-0" @click="handleOpenAdd">
            新增配置账号
          </n-button>
        </div>

        <!-- 卡片网格 -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 accounts-stagger">
          <div
            v-for="acc in accountStore.accounts"
            :key="acc.id"
            class="account-card bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-6 shadow-sm hover:shadow-card-hover hover:border-primary/30 dark:hover:border-primary/30 flex flex-col justify-between select-none"
          >
            <div>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
                    <Icon icon="lucide:user" :width="18" />
                  </div>
                  <div>
                    <h4 class="font-bold text-slate-800 dark:text-slate-200 text-sm leading-tight">{{ acc.account_alias }}</h4>
                    <span class="text-[9px] text-slate-400 dark:text-slate-500 font-mono">ID: {{ acc.id }}</span>
                  </div>
                </div>
                
                <!-- 编辑按钮 -->
                <n-button size="tiny" quaternary type="primary" @click="handleEdit(acc)">
                  <template #icon><Icon icon="lucide:edit-2" /></template>
                </n-button>
              </div>

              <!-- 卡片指标 -->
              <div class="mt-5 space-y-3 text-xs">
                <div class="flex justify-between items-center">
                  <span class="text-slate-400 dark:text-slate-500">AccessKey ID</span>
                  <span class="font-mono text-slate-750 dark:text-slate-350 bg-slate-50 dark:bg-slate-900 border border-borderLight dark:border-borderDark px-2 py-0.5 rounded">{{ maskKey(acc.access_key_id) }}</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-slate-400 dark:text-slate-500">云服务器 ECS</span>
                  <span class="font-bold text-primary">{{ getEcsCount(acc.account_alias) }} 台</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-slate-400 dark:text-slate-500">弹性公网 IP</span>
                  <span class="font-bold text-indigo-500">{{ getEipCount(acc.account_alias) }} 个</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-slate-400 dark:text-slate-500">托管资源数</span>
                  <span class="font-bold text-success">{{ getResourceCount(acc.account_alias) }} 个</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-slate-400 dark:text-slate-500">活跃同步地域</span>
                  <div class="flex flex-wrap gap-1 justify-end max-w-[200px]">
                    <span
                      v-for="reg in (acc.active_regions || [])"
                      :key="reg"
                      class="inline-block px-1.5 py-0.5 rounded bg-sky-500/10 dark:bg-sky-500/15 text-sky-600 dark:text-sky-400 text-[9px] font-normal font-mono leading-none"
                    >
                      {{ getRegionName(reg) }}
                    </span>
                    <span v-if="!acc.active_regions || acc.active_regions.length === 0" class="text-slate-400 text-[9.5px]">暂无 / 首次同步中</span>
                  </div>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-slate-400 dark:text-slate-500">自动同步策略</span>
                  <span class="font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200/60 dark:border-emerald-800/40 px-2 py-0.5 rounded text-[11px]">{{ formatSyncInterval(acc.sync_interval) }}</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-slate-400 dark:text-slate-500">上次尝试同步</span>
                  <span class="font-mono text-slate-700 dark:text-slate-300">{{ formatDate(acc.last_attempted_at) }}</span>
                </div>
                <div class="flex justify-between items-center">
                  <span class="text-slate-400 dark:text-slate-500">上次成功同步</span>
                  <span class="font-mono text-slate-700 dark:text-slate-300">{{ formatDate(acc.last_synced_at) }}</span>
                </div>
              </div>
            </div>

            <div class="mt-6 pt-4 border-t border-borderLight dark:border-borderDark flex items-center gap-3">
              <n-button size="small" type="primary" :loading="syncStore.syncingAccounts.includes(Number(acc.id))" @click="handleSyncAccount(acc)" class="flex-1">立即同步</n-button>
              <n-popconfirm @positive-click="handleDelete(acc.id)" positive-text="确认" negative-text="取消">
                <template #trigger>
                  <n-button size="small" quaternary type="error">
                    <template #icon><Icon icon="lucide:trash-2" /></template>
                  </n-button>
                </template>
                确认删除此账号及对应资产？此操作无法撤销。
              </n-popconfirm>
            </div>
          </div>
        </div>

        <!-- 暂无账号卡片 -->
        <div v-if="accountStore.accounts.length === 0" class="flex flex-col items-center justify-center p-16 bg-white dark:bg-cardDark border border-dashed border-borderLight dark:border-borderDark rounded-xl shadow-sm">
          <Icon icon="lucide:users" :width="32" class="text-slate-400 dark:text-slate-500 mb-3" />
          <h3 class="text-sm font-semibold text-slate-800 dark:text-slate-200">暂无配置阿里云账号</h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 mb-5">立即添加您的 AccessKey，系统将在后台自动拉取所有 ECS、EIP、域名与证书。</p>
          <n-button type="primary" @click="handleOpenAdd">立即添加配置</n-button>
        </div>

    <!-- 添加/编辑账号 Modal -->
    <n-modal v-model:show="showAddModal" preset="card" :title="isEditMode ? '编辑云凭证' : '配置新云凭证'" style="width: 500px;" class="rounded-xl shadow-card">
      <n-form :model="formData" :rules="formRules" ref="formRef" class="space-y-4 py-2">
        <n-form-item label="账号别名 (如：公司主账号、RAM测试账号)" path="alias">
          <n-input v-model:value="formData.alias" placeholder="请输入易于识别的别名，例如 '阿里云主账号'" class="rounded-lg" />
        </n-form-item>
        <n-form-item label="AccessKey ID" path="ak">
          <n-input v-model:value="formData.ak" placeholder="输入阿里云 AccessKey ID" class="rounded-lg font-mono" />
        </n-form-item>
        <n-form-item label="AccessKey Secret" path="sk">
          <n-input v-model:value="formData.sk" type="password" show-password-on="mousedown" :placeholder="isEditMode ? '不修改请留空' : '输入阿里云 AccessKey Secret'" class="rounded-lg font-mono" />
        </n-form-item>
        <n-form-item label="自动同步频率" path="interval">
          <n-select v-model:value="formData.interval" :options="intervalOptions" class="rounded-lg" />
        </n-form-item>
      </n-form>

      <template #action>
        <div class="flex justify-end gap-2.5">
          <n-button @click="showAddModal = false">取消</n-button>
          <n-button type="primary" :loading="submitting" @click="handleSubmit">确认保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { useMessage } from 'naive-ui'
import { useAccountStore, useResourceStore, useSyncStore } from '@/store'

const accountStore = useAccountStore()
const resourceStore = useResourceStore()
const syncStore = useSyncStore()
const message = useMessage()

const showAddModal = ref(false)
const submitting = ref(false)
const isEditMode = ref(false)
const editingAccountId = ref<number | null>(null)

const formRef = ref<any>(null)
const formData = reactive({
  alias: '',
  ak: '',
  sk: '',
  interval: 168,
})

const formRules = computed(() => {
  return {
    alias: { required: true, message: '请输入别名', trigger: 'blur' },
    ak: { required: true, message: '请输入 AccessKey ID', trigger: 'blur' },
    sk: { required: !isEditMode.value, message: '请输入 AccessKey Secret', trigger: 'blur' },
  }
})

const intervalOptions = [
  { label: '每周一凌晨同步', value: 168 },
  { label: '每月 1 号凌晨同步', value: 720 },
  { label: '每天凌晨自动同步', value: 24 },
  { label: '纯手动同步', value: 0 },
]

import { fetchResources } from '@/api'
import type { ResourceItem } from '@/api'

const unfilteredEcs = ref<ResourceItem[]>([])
const unfilteredEip = ref<ResourceItem[]>([])
const unfilteredDomain = ref<ResourceItem[]>([])
const unfilteredSsl = ref<ResourceItem[]>([])

async function loadAllAccountsStatistics() {
  try {
    const [ecs, eip, domain, ssl] = await Promise.all([
      fetchResources('ECS'),
      fetchResources('EIP'),
      fetchResources('Domain'),
      fetchResources('SSL')
    ])
    unfilteredEcs.value = ecs
    unfilteredEip.value = eip
    unfilteredDomain.value = domain
    unfilteredSsl.value = ssl
  } catch (e) {
    console.error('Failed to load accounts statistics:', e)
  }
}

onMounted(async () => {
  await accountStore.loadAccounts()
  await Promise.all([
    resourceStore.loadAllResources(),
    loadAllAccountsStatistics()
  ])
})

function maskKey(key: string): string {
  if (!key || key.length < 8) return key
  return key.substring(0, 4) + '...' + key.substring(key.length - 4)
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

function formatDate(dateStr?: string): string {
  if (!dateStr) return '暂无数据'
  try {
    const d = new Date(dateStr)
    if (isNaN(d.getTime())) return dateStr
    return d.toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
  } catch (e) {
    return dateStr
  }
}

function formatSyncInterval(interval?: number): string {
  if (interval === 168) return '每周一凌晨'
  if (interval === 720) return '每月 1 号凌晨'
  if (interval === 24) return '每天凌晨'
  if (interval === 0) return '纯手动同步'
  if (interval === undefined || interval === null) return '每周一凌晨'
  return `${interval} 小时/次`
}

function getEcsCount(accountAlias: string): number {
  return unfilteredEcs.value.filter((r) => r.account_name === accountAlias).length
}

function getEipCount(accountAlias: string): number {
  return unfilteredEip.value.filter((r) => r.account_name === accountAlias).length
}

function getResourceCount(accountAlias: string): number {
  const ecs = getEcsCount(accountAlias)
  const eip = getEipCount(accountAlias)
  const dom = unfilteredDomain.value.filter((r) => r.account_name === accountAlias).length
  const ssl = unfilteredSsl.value.filter((r) => r.account_name === accountAlias).length
  return ecs + eip + dom + ssl
}

function handleOpenAdd() {
  isEditMode.value = false
  editingAccountId.value = null
  formData.alias = ''
  formData.ak = ''
  formData.sk = ''
  formData.interval = 24
  showAddModal.value = true
}

function handleEdit(acc: any) {
  isEditMode.value = true
  editingAccountId.value = acc.id
  formData.alias = acc.account_alias
  formData.ak = acc.access_key_id
  formData.sk = ''
  formData.interval = acc.sync_interval
  showAddModal.value = true
}

async function handleSyncAccount(acc: any) {
  try {
    message.info(`正在触发 [${acc.account_alias}] 的同步任务`)
    const res = await syncStore.triggerSingleAccountSync(acc.id, acc.account_alias)
    if (res && res.status === 'already_running') {
      message.warning(`账号 [${acc.account_alias}] 正在同步中，请勿重复触发`)
    } else {
      message.success('已下发同步指令，同步进度在顶部查看')
    }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '触发同步失败，同步队列或服务不可用'
    message.error(msg)
  }
}

async function handleDelete(id: number) {
  try {
    await accountStore.removeAccount(id)
    message.success('账号已成功删除')
    await Promise.all([
      resourceStore.loadAllResources(),
      loadAllAccountsStatistics()
    ])
  } catch (e) {
    message.error('删除账号失败')
  }
}

function cleanCredentialFrontend(val: string): string {
  if (!val) return ''
  let cleaned = val.trim()
  const prefixes = ['ak:', 'sk:', 'ak：', 'sk：']
  for (const prefix of prefixes) {
    if (cleaned.toLowerCase().startsWith(prefix)) {
      cleaned = cleaned.substring(prefix.length).trim()
    }
  }
  if (cleaned.startsWith('"') && cleaned.endsWith('"')) {
    cleaned = cleaned.substring(1, cleaned.length - 1).trim()
  } else if (cleaned.startsWith("'") && cleaned.endsWith("'")) {
    cleaned = cleaned.substring(1, cleaned.length - 1).trim()
  }
  return cleaned
}

function handleSubmit() {
  formRef.value?.validate(async (errors: any) => {
    if (errors) return
    submitting.value = true
    try {
      const cleanAlias = formData.alias.trim()
      const cleanAk = cleanCredentialFrontend(formData.ak)
      const cleanSk = formData.sk ? cleanCredentialFrontend(formData.sk) : ''
      
      let res: any = null
      if (isEditMode.value && editingAccountId.value !== null) {
        const payload: any = {
          account_alias: cleanAlias,
          access_key_id: cleanAk,
          sync_interval: formData.interval
        }
        if (cleanSk) {
          payload.access_key_secret = cleanSk
        }
        res = await accountStore.updateAccount(editingAccountId.value, payload)
      } else {
        res = await accountStore.addAccount(cleanAlias, cleanAk, cleanSk, formData.interval)
      }

      if (res && res.warning) {
        message.warning(res.warning)
      } else {
        message.success(isEditMode.value ? '凭证更新成功' : '凭证保存成功，已自动在后台开启数据同步')
      }

      if (res && res.sync_queued && res.task_id) {
        syncStore.trackSyncTask(res.task_id, res.data?.account_alias || cleanAlias, isEditMode.value ? editingAccountId.value! : (res.data?.id))
      }

      showAddModal.value = false
      await loadAllAccountsStatistics()
      await accountStore.loadAccounts()
      await resourceStore.loadAllResources()
    } catch (e: any) {
      const msg = e?.response?.data?.detail || (isEditMode.value ? '云账号更新失败' : '云账号保存失败')
      message.error(msg)
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped>
.accounts-stagger > * {
  animation: fadeUp 240ms cubic-bezier(0.23, 1, 0.32, 1) backwards;
}
.accounts-stagger > *:nth-child(1) { animation-delay: 0ms; }
.accounts-stagger > *:nth-child(2) { animation-delay: 40ms; }
.accounts-stagger > *:nth-child(3) { animation-delay: 80ms; }
.accounts-stagger > *:nth-child(4) { animation-delay: 120ms; }
.accounts-stagger > *:nth-child(5) { animation-delay: 160ms; }
.accounts-stagger > *:nth-child(6) { animation-delay: 200ms; }

.account-card {
  transition: transform 180ms cubic-bezier(0.23, 1, 0.32, 1), box-shadow 180ms ease, border-color 180ms ease;
}

@media (hover: hover) and (pointer: fine) {
  .account-card:hover {
    transform: translateY(-2px);
  }
}
</style>
