<template>
  <div class="space-y-3.5 w-full">
    <!-- 头部简洁 Banner -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 px-4 py-3 rounded-lg shadow-sm">
      <div class="flex items-center gap-2.5">
        <div class="w-7 h-7 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
          <Icon icon="lucide:settings" :width="15" />
        </div>
        <div>
          <h1 class="text-base font-bold tracking-tight text-slate-900 dark:text-slate-100">系统配置中心</h1>
        </div>
        <span class="text-xs text-slate-400 dark:text-slate-500 border-l border-slate-200 dark:border-slate-700 pl-2.5 ml-1">
          域名预警 · 同步策略 · 系统偏好
        </span>
      </div>
    </div>

    <!-- 域名到期钉钉智能预警 (精致紧凑双栏布局) -->
    <div class="bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl shadow-sm overflow-hidden">
      <!-- 头部：标题与总开关 -->
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-900/20">
        <div class="flex items-center gap-2.5">
          <div class="w-6 h-6 rounded-md bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
            <Icon icon="lucide:bell-ring" :width="14" />
          </div>
          <span class="text-xs font-bold text-slate-800 dark:text-slate-200">域名到期钉钉智能预警</span>
          <span
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-medium"
            :class="settingStore.domainAlertEnabled ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'"
          >
            <span class="w-1.5 h-1.5 rounded-full" :class="settingStore.domainAlertEnabled ? 'bg-emerald-500' : 'bg-slate-400'" />
            {{ settingStore.domainAlertEnabled ? '告警运行中' : '已停用' }}
          </span>
          <span class="text-[11px] text-slate-400 hidden sm:inline">（每天 09:00 自动巡检，智能避开节假日与周末）</span>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-[11px] font-medium text-slate-500">总开关</span>
          <n-switch v-model:value="settingStore.domainAlertEnabled" size="small" />
        </div>
      </div>

      <!-- 表单主体：左右紧凑双栏 -->
      <div v-if="settingStore.loaded && credentialsLoaded" class="p-4">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
          <!-- 左侧 7 列：钉钉通道设置 -->
          <div class="lg:col-span-7 space-y-3">
            <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800/80 pb-1.5">
              <span class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Icon icon="lucide:send" :width="13" class="text-blue-500" />
                钉钉通道接入凭据
              </span>
              <span
                class="text-[11px] font-medium"
                :class="settingStore.webhookConfigured ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'"
              >
                {{ settingStore.webhookConfigured ? '● Webhook 已配置' : '○ 暂未配置' }}
              </span>
            </div>

            <!-- Webhook 地址 -->
            <div class="space-y-1">
              <label class="text-[11px] font-semibold text-slate-600 dark:text-slate-300 flex items-center gap-1">
                <span>Webhook 地址</span>
                <span class="text-red-500">*</span>
              </label>
              <n-input
                v-model:value="webhook"
                type="password"
                size="small"
                show-password-on="click"
                class="font-mono text-xs"
                :placeholder="settingStore.webhookConfigured ? 'Webhook 地址已加密保存；输入新地址可替换' : '请输入钉钉机器人 Webhook 地址'"
              >
                <template #prefix>
                  <Icon icon="lucide:link-2" class="text-slate-400 mr-1" />
                </template>
              </n-input>
            </div>

            <!-- 关键词 与 加签 Secret (双列紧凑并排) -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-0.5">
              <div class="space-y-1">
                <label class="text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                  安全自定义关键词 (可选)
                </label>
                <n-input
                  v-model:value="settingStore.dingKeyword"
                  maxlength="100"
                  size="small"
                  class="text-xs"
                  placeholder="默认：域名告警"
                >
                  <template #prefix>
                    <Icon icon="lucide:tag" class="text-slate-400 mr-1" />
                  </template>
                </n-input>
              </div>

              <div class="space-y-1">
                <div class="flex items-center justify-between">
                  <label class="text-[11px] font-semibold text-slate-600 dark:text-slate-300">
                    加签 Secret (可选)
                  </label>
                  <span class="text-[10px]" :class="settingStore.secretConfigured ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-slate-400'">
                    {{ settingStore.secretConfigured ? '● 已加签' : '○ 未加签' }}
                  </span>
                </div>
                <n-input
                  v-model:value="dingSecret"
                  type="password"
                  size="small"
                  show-password-on="click"
                  class="font-mono text-xs"
                  :placeholder="settingStore.secretConfigured ? 'Secret 已保存；输入新值替换' : 'SEC 开头的加签密钥'"
                >
                  <template #prefix>
                    <Icon icon="lucide:shield-check" class="text-slate-400 mr-1" />
                  </template>
                </n-input>
              </div>
            </div>
          </div>

          <!-- 右侧 5 列：到期阶梯预警阈值 -->
          <div class="lg:col-span-5 bg-slate-50/70 dark:bg-slate-900/40 border border-slate-200/80 dark:border-slate-800 p-3 rounded-lg space-y-2.5">
            <div class="flex items-center justify-between border-b border-slate-200/60 dark:border-slate-800 pb-1.5">
              <span class="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                <Icon icon="lucide:layers" :width="13" class="text-amber-500" />
                到期阶梯预警阈值
              </span>
              <span class="text-[10px] text-slate-400">提醒 &gt; 告警 &gt; 严重</span>
            </div>

            <div class="space-y-1.5">
              <!-- 常规提醒 -->
              <div class="flex items-center justify-between bg-white dark:bg-cardDark border border-slate-200/60 dark:border-slate-800 px-2.5 py-1.5 rounded-md">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-blue-500" />
                  <span class="text-xs text-slate-700 dark:text-slate-300 font-medium">常规提醒天数</span>
                </div>
                <n-input-number
                  v-model:value="settingStore.reminderDays"
                  :min="1"
                  :max="365"
                  size="small"
                  class="w-20 text-right"
                >
                  <template #suffix>天</template>
                </n-input-number>
              </div>

              <!-- 重点告警 -->
              <div class="flex items-center justify-between bg-white dark:bg-cardDark border border-slate-200/60 dark:border-slate-800 px-2.5 py-1.5 rounded-md">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-amber-500" />
                  <span class="text-xs text-slate-700 dark:text-slate-300 font-medium">重点告警天数</span>
                </div>
                <n-input-number
                  v-model:value="settingStore.warningDays"
                  :min="1"
                  :max="365"
                  size="small"
                  class="w-20 text-right"
                >
                  <template #suffix>天</template>
                </n-input-number>
              </div>

              <!-- 紧急严重 -->
              <div class="flex items-center justify-between bg-white dark:bg-cardDark border border-slate-200/60 dark:border-slate-800 px-2.5 py-1.5 rounded-md">
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-rose-500" />
                  <span class="text-xs text-slate-700 dark:text-slate-300 font-medium">紧急严重天数</span>
                </div>
                <n-input-number
                  v-model:value="settingStore.criticalDays"
                  :min="0"
                  :max="365"
                  size="small"
                  class="w-20 text-right"
                >
                  <template #suffix>天</template>
                </n-input-number>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 加载中占位 -->
      <div v-else class="py-8 flex flex-col items-center justify-center text-slate-400 space-y-1.5">
        <Icon icon="lucide:loader-2" class="animate-spin text-blue-500" :width="20" />
        <span class="text-xs">正在加载配置...</span>
      </div>

      <!-- 底部紧凑操作条 -->
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between px-4 py-2.5 border-t border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/20 gap-2.5">
        <span class="text-[11px] text-slate-400 flex items-center gap-1.5">
          <Icon icon="lucide:shield-check" :width="13" class="text-emerald-500" />
          保存后自动加密落盘并触发连通性校验
        </span>
        <div class="flex items-center gap-2 w-full sm:w-auto justify-end">
          <n-button size="small" secondary :loading="testing" @click="testDomainAlert">
            <template #icon><Icon icon="lucide:send" :width="13" /></template>
            发送测试
          </n-button>
          <n-button size="small" type="primary" :loading="saving" @click="saveDomainAlert">
            <template #icon><Icon icon="lucide:save" :width="13" /></template>
            保存配置
          </n-button>
        </div>
      </div>
    </div>

    <!-- 底部双列紧凑卡片 (同步周期 + 外观偏好) -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3.5">
      <!-- 自动同步设置 (基于各个账号配置) -->
      <div class="bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl p-4 shadow-sm space-y-3 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
            <div class="flex items-center gap-2">
              <div class="w-6 h-6 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                <Icon icon="lucide:refresh-cw" :width="13" />
              </div>
              <h3 class="text-xs font-bold text-slate-800 dark:text-slate-200">云账号数据同步周期</h3>
            </div>
            <span class="text-[10.5px] text-slate-400">推荐每周一 03:00</span>
          </div>

          <div class="mt-2.5 space-y-2 max-h-[170px] overflow-y-auto pr-1 custom-scroll">
            <div
              v-for="acc in accountStore.accounts"
              :key="acc.id"
              class="flex justify-between items-center bg-slate-50/80 dark:bg-slate-900/50 border border-slate-200/60 dark:border-slate-800 px-3 py-2 rounded-lg"
            >
              <div class="flex items-center gap-2 truncate mr-2">
                <Icon icon="lucide:user" :width="13" class="text-slate-400 shrink-0" />
                <span class="text-xs font-bold text-slate-800 dark:text-slate-200 truncate">{{ acc.account_alias }}</span>
              </div>
              <n-select
                v-model:value="acc.sync_interval"
                :options="intervalOptions"
                size="small"
                style="width: 155px"
                @update:value="(val: any) => handleIntervalChange(acc.id, val)"
              />
            </div>
            <div v-if="accountStore.accounts.length === 0" class="py-6 text-center text-xs text-slate-400">
              暂无已配置云账号
            </div>
          </div>
        </div>

        <p class="text-[11px] text-slate-400 dark:text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800">
          💡 后台异步队列平滑执行，账号间缓冲 1.5s，降低 96% API 消耗。
        </p>
      </div>

      <!-- 界面主题配置 & 系统信息 -->
      <div class="bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl p-4 shadow-sm space-y-3 flex flex-col justify-between">
        <div>
          <div class="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-2">
            <div class="w-6 h-6 rounded-md bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <Icon icon="lucide:palette" :width="13" />
            </div>
            <h3 class="text-xs font-bold text-slate-800 dark:text-slate-200">外观主题与系统信息</h3>
          </div>

          <div class="mt-2.5 space-y-2 text-xs">
            <div class="flex items-center justify-between bg-slate-50/80 dark:bg-slate-900/50 border border-slate-200/60 dark:border-slate-800 p-2.5 rounded-lg">
              <span class="font-semibold text-slate-700 dark:text-slate-300">系统外观风格</span>
              <n-radio-group v-model:value="themeStore.theme" size="small" @update:value="handleThemeChange">
                <n-radio-button value="dark">
                  <div class="flex items-center gap-1"><Icon icon="lucide:moon" :width="12" /> 深色</div>
                </n-radio-button>
                <n-radio-button value="light">
                  <div class="flex items-center gap-1"><Icon icon="lucide:sun" :width="12" /> 浅色</div>
                </n-radio-button>
              </n-radio-group>
            </div>

            <div class="bg-slate-50/80 dark:bg-slate-900/50 border border-slate-200/60 dark:border-slate-800 p-2.5 rounded-lg space-y-1">
              <div class="flex justify-between items-center text-[11px]">
                <span class="text-slate-400">系统版本</span>
                <span class="font-bold font-mono text-slate-700 dark:text-slate-200">v2.1.0 Enterprise</span>
              </div>
              <div class="flex justify-between items-center text-[11px] pt-1 border-t border-slate-200/40 dark:border-slate-800">
                <span class="text-slate-400">技术架构</span>
                <span class="font-mono text-slate-600 dark:text-slate-300">FastAPI + Vue3 + APScheduler</span>
              </div>
            </div>
          </div>
        </div>

        <p class="text-[11px] text-slate-400 dark:text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800">
          深浅双主题支持物理按压微动效与视网膜高分屏。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Icon } from '@iconify/vue'
import { useMessage } from 'naive-ui'
import { fetchDomainAlertCredentials } from '@/api'
import { useThemeStore, useSettingStore, useAccountStore } from '@/store'

const themeStore = useThemeStore()
const settingStore = useSettingStore()
const accountStore = useAccountStore()
const message = useMessage()
const webhook = ref('')
const dingSecret = ref('')
const saving = ref(false)
const testing = ref(false)
const credentialsLoaded = ref(false)

onMounted(async () => {
  await Promise.all([settingStore.loadSettings(), accountStore.loadAccounts()])
  await revealCredentials()
})

const intervalOptions = [
  { label: '每周一凌晨同步', value: 168 },
  { label: '每月 1 号凌晨同步', value: 720 },
  { label: '每天凌晨自动同步', value: 24 },
  { label: '纯手动同步', value: 0 },
]

function apiError(error: any): string {
  return error?.response?.data?.detail || error?.message || '操作失败'
}

async function saveDomainAlert() {
  if (settingStore.domainAlertEnabled && !webhook.value && !settingStore.webhookConfigured) {
    message.warning('启用告警时，必须输入钉钉机器人 Webhook 地址')
    return
  }

  saving.value = true
  try {
    const payload: any = {
      enabled: settingStore.domainAlertEnabled,
      reminder_days: settingStore.reminderDays,
      warning_days: settingStore.warningDays,
      critical_days: settingStore.criticalDays,
      keyword: settingStore.dingKeyword.trim() || '域名告警',
    }

    if (webhook.value.trim()) {
      payload.webhook = webhook.value.trim()
    }
    if (dingSecret.value.trim()) {
      payload.secret = dingSecret.value.trim()
    }

    await settingStore.updateDomainAlert(payload)
    message.success('钉钉域名告警配置已成功保存！')
    webhook.value = ''
    dingSecret.value = ''
    await revealCredentials()
  } catch (error: any) {
    message.error(apiError(error))
  } finally {
    saving.value = false
  }
}

async function testDomainAlert() {
  if (!settingStore.webhookConfigured && !webhook.value.trim()) {
    message.warning('请先输入钉钉 Webhook 地址或保存后再测试')
    return
  }

  testing.value = true
  try {
    await settingStore.testDomainAlert()
    message.success('测试消息已成功发送至钉钉群，请在群聊中查收！')
  } catch (error: any) {
    message.error(apiError(error))
  } finally {
    testing.value = false
  }
}

async function handleThemeChange(theme: 'light' | 'dark') {
  themeStore.toggleTheme()
  message.info(`已切换为${theme === 'dark' ? '深色' : '浅色'}模式`)
}

async function handleIntervalChange(id: number, val: number) {
  try {
    await accountStore.updateAccount(id, { sync_interval: val })
    message.success('已更新该云账号的定时同步周期')
  } catch (error: any) {
    message.error(apiError(error))
  }
}

async function revealCredentials() {
  credentialsLoaded.value = false
  try {
    const creds = await fetchDomainAlertCredentials()
    if (creds.webhook) {
      webhook.value = creds.webhook
    }
    if (creds.secret) {
      dingSecret.value = creds.secret
    }
  } catch (e) {
    // 静默降级
  } finally {
    credentialsLoaded.value = true
  }
}
</script>

<style scoped>
.custom-scroll::-webkit-scrollbar {
  width: 4px;
}
.custom-scroll::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.3);
  border-radius: 4px;
}
:global(.dark) .custom-scroll::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.2);
}
</style>
