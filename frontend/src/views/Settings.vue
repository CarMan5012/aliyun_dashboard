<template>
  <div class="space-y-5 max-w-6xl mx-auto">
    <!-- 头部标题 Banner -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 px-5 py-4 rounded-xl shadow-sm">
      <div>
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
            <Icon icon="lucide:settings" :width="18" />
          </div>
          <h1 class="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">系统配置中心</h1>
        </div>
        <p class="mt-1 text-xs text-slate-500 dark:text-slate-400 font-medium">
          集中管理域名到期钉钉预警、多账号自动同步周期与系统外观偏好
        </p>
      </div>
    </div>

    <!-- 域名到期钉钉告警卡片 (重点重新设计) -->
    <div class="bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl shadow-sm overflow-hidden">
      <!-- 卡片头部 -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/30 gap-3">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center">
            <Icon icon="lucide:bell-ring" :width="18" />
          </div>
          <div>
            <div class="flex items-center gap-2">
              <h3 class="text-sm font-bold text-slate-900 dark:text-slate-100">域名到期钉钉智能预警</h3>
              <span
                class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium"
                :class="settingStore.domainAlertEnabled ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'"
              >
                <span class="w-1.5 h-1.5 rounded-full" :class="settingStore.domainAlertEnabled ? 'bg-emerald-500' : 'bg-slate-400'" />
                {{ settingStore.domainAlertEnabled ? '告警已启用' : '未启用' }}
              </span>
            </div>
            <p class="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              每天上午 09:00 自动巡检本地数据库，智能避开节假日与周末，并在工作日准时推送群提醒
            </p>
          </div>
        </div>

        <div class="flex items-center gap-3">
          <span class="text-xs font-semibold text-slate-700 dark:text-slate-300">告警总开关</span>
          <n-switch v-model:value="settingStore.domainAlertEnabled" size="medium" />
        </div>
      </div>

      <!-- 表单主体网格 -->
      <div v-if="settingStore.loaded && credentialsLoaded" class="p-6">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-8">
          <!-- 左侧 7 列：钉钉机器人通道配置 -->
          <div class="lg:col-span-7 space-y-4">
            <div class="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
              <h4 class="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                <Icon icon="lucide:send" :width="14" class="text-primary" />
                钉钉机器人接入凭据
              </h4>
              <span
                class="text-[11px] px-2 py-0.5 rounded"
                :class="settingStore.webhookConfigured ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 font-medium' : 'bg-slate-100 dark:bg-slate-800 text-slate-400'"
              >
                {{ settingStore.webhookConfigured ? '● Webhook 已就绪' : '○ 暂未配置' }}
              </span>
            </div>

            <!-- Webhook 输入 -->
            <div class="space-y-1.5">
              <label class="text-xs font-semibold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                <span>钉钉 Webhook 地址 <span class="text-red-500">*</span></span>
              </label>
              <n-input
                v-model:value="webhook"
                type="password"
                size="medium"
                show-password-on="click"
                class="rounded-lg font-mono text-xs"
                :placeholder="settingStore.webhookConfigured ? 'Webhook 已安全保存；如需修改请输入新地址' : 'https://oapi.dingtalk.com/robot/send?access_token=...'"
              >
                <template #prefix>
                  <Icon icon="lucide:link-2" class="text-slate-400 mr-1" />
                </template>
              </n-input>
            </div>

            <!-- 关键词与加签 Secret -->
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
              <div class="space-y-1.5">
                <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">
                  安全自定义关键词 (可选)
                </label>
                <n-input
                  v-model:value="settingStore.dingKeyword"
                  maxlength="100"
                  size="medium"
                  class="rounded-lg text-xs"
                  placeholder="如：告警 / 阿里云资产"
                >
                  <template #prefix>
                    <Icon icon="lucide:tag" class="text-slate-400 mr-1" />
                  </template>
                </n-input>
              </div>

              <div class="space-y-1.5">
                <div class="flex items-center justify-between">
                  <label class="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    加签 Secret 密钥 (可选)
                  </label>
                  <span class="text-[11px]" :class="settingStore.secretConfigured ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-slate-400'">
                    {{ settingStore.secretConfigured ? '已配置' : '未配置' }}
                  </span>
                </div>
                <n-input
                  v-model:value="dingSecret"
                  type="password"
                  size="medium"
                  show-password-on="click"
                  class="rounded-lg font-mono text-xs"
                  :placeholder="settingStore.secretConfigured ? 'Secret 已保存；输入新值替换' : 'SEC 开头的加签密钥'"
                >
                  <template #prefix>
                    <Icon icon="lucide:shield-check" class="text-slate-400 mr-1" />
                  </template>
                </n-input>
              </div>
            </div>
          </div>

          <!-- 右侧 5 列：告警阶梯天数配置 -->
          <div class="lg:col-span-5 bg-slate-50/70 dark:bg-slate-900/40 border border-slate-200/80 dark:border-slate-800 p-4 rounded-xl flex flex-col justify-between space-y-4">
            <div>
              <h4 class="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5 border-b border-slate-200/60 dark:border-slate-800 pb-2 mb-3">
                <Icon icon="lucide:layers" :width="14" class="text-amber-500" />
                到期阶梯预警阈值
              </h4>

              <div class="space-y-2.5">
                <!-- 提醒天数 -->
                <div class="flex items-center justify-between bg-white dark:bg-cardDark border border-slate-200/60 dark:border-slate-800 px-3.5 py-2.5 rounded-lg">
                  <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-sm" />
                    <div>
                      <span class="text-xs font-bold text-slate-800 dark:text-slate-200">常规提醒天数</span>
                      <p class="text-[10px] text-slate-400">第一阶段温和提示</p>
                    </div>
                  </div>
                  <n-input-number
                    v-model:value="settingStore.reminderDays"
                    :min="1"
                    :max="365"
                    size="small"
                    class="w-24 text-right"
                  >
                    <template #suffix>天</template>
                  </n-input-number>
                </div>

                <!-- 告警天数 -->
                <div class="flex items-center justify-between bg-white dark:bg-cardDark border border-slate-200/60 dark:border-slate-800 px-3.5 py-2.5 rounded-lg">
                  <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-sm" />
                    <div>
                      <span class="text-xs font-bold text-slate-800 dark:text-slate-200">重点告警天数</span>
                      <p class="text-[10px] text-slate-400">第二阶段重点关注</p>
                    </div>
                  </div>
                  <n-input-number
                    v-model:value="settingStore.warningDays"
                    :min="1"
                    :max="365"
                    size="small"
                    class="w-24 text-right"
                  >
                    <template #suffix>天</template>
                  </n-input-number>
                </div>

                <!-- 严重天数 -->
                <div class="flex items-center justify-between bg-white dark:bg-cardDark border border-slate-200/60 dark:border-slate-800 px-3.5 py-2.5 rounded-lg">
                  <div class="flex items-center gap-2">
                    <span class="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-sm" />
                    <div>
                      <span class="text-xs font-bold text-slate-800 dark:text-slate-200">紧急严重天数</span>
                      <p class="text-[10px] text-slate-400">临近停服极度紧急</p>
                    </div>
                  </div>
                  <n-input-number
                    v-model:value="settingStore.criticalDays"
                    :min="0"
                    :max="365"
                    size="small"
                    class="w-24 text-right"
                  >
                    <template #suffix>天</template>
                  </n-input-number>
                </div>
              </div>
            </div>

            <div class="text-[11px] text-slate-500 dark:text-slate-400 bg-blue-50/50 dark:bg-blue-950/20 p-2.5 rounded-lg border border-blue-100 dark:border-blue-900/30 flex items-start gap-1.5 leading-relaxed">
              <Icon icon="lucide:info" :width="14" class="text-blue-500 shrink-0 mt-0.5" />
              <span>规则逻辑：常规提醒 &gt; 重点告警 &gt; 紧急严重。同一阶段内仅推送一次，避免刷屏骚扰。</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 正在加载占位 -->
      <div v-else class="py-12 flex flex-col items-center justify-center text-slate-400 space-y-2">
        <Icon icon="lucide:loader-2" class="animate-spin text-primary" :width="24" />
        <span class="text-xs">正在安全加载告警凭据与配置...</span>
      </div>

      <!-- 卡片底部操作栏 -->
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between px-6 py-3.5 border-t border-slate-100 dark:border-slate-800 bg-slate-50/30 dark:bg-slate-900/20 gap-3">
        <span class="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
          <Icon icon="lucide:check-circle-2" :width="14" class="text-emerald-500" />
          保存后自动加密落盘并触发一次即时连通性检测
        </span>
        <div class="flex items-center gap-3 w-full sm:w-auto justify-end">
          <n-button size="medium" secondary :loading="testing" @click="testDomainAlert">
            <template #icon><Icon icon="lucide:send" /></template>
            发送测试消息
          </n-button>
          <n-button size="medium" type="primary" :loading="saving" @click="saveDomainAlert">
            <template #icon><Icon icon="lucide:save" /></template>
            保存配置
          </n-button>
        </div>
      </div>
    </div>

    <!-- 底部双列卡片 (同步周期 + 界面偏好) -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
      <!-- 自动同步设置 (基于各个账号配置) -->
      <div class="bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl p-5 shadow-sm space-y-4 flex flex-col justify-between">
        <div>
          <div class="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
            <div class="w-7 h-7 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <Icon icon="lucide:refresh-cw" :width="15" />
            </div>
            <div>
              <h3 class="text-sm font-bold text-slate-900 dark:text-slate-100">云账号数据同步周期</h3>
              <p class="text-[11px] text-slate-400">配置各个云账号后台自动拉取的调度频率</p>
            </div>
          </div>

          <div class="mt-4 space-y-2.5 max-h-[220px] overflow-y-auto pr-1 custom-scroll">
            <div
              v-for="acc in accountStore.accounts"
              :key="acc.id"
              class="flex justify-between items-center bg-slate-50/80 dark:bg-slate-900/50 border border-slate-200/60 dark:border-slate-800 px-4 py-2.5 rounded-lg"
            >
              <div class="flex items-center gap-2">
                <Icon icon="lucide:user" :width="14" class="text-slate-400" />
                <span class="text-xs font-bold text-slate-800 dark:text-slate-200">{{ acc.account_alias }}</span>
              </div>
              <n-select
                v-model:value="acc.sync_interval"
                :options="intervalOptions"
                size="small"
                style="width: 170px"
                @update:value="(val: any) => handleIntervalChange(acc.id, val)"
              />
            </div>
            <div v-if="accountStore.accounts.length === 0" class="py-8 text-center text-xs text-slate-400">
              暂无已配置云账号
            </div>
          </div>
        </div>

        <p class="text-[11px] text-slate-400 dark:text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800">
          💡 生产环境推荐「每周一凌晨同步」，大幅降低 96% 阿里云 API 调用消耗。
        </p>
      </div>

      <!-- 界面主题配置 & 系统信息 -->
      <div class="bg-white dark:bg-cardDark border border-slate-200/80 dark:border-slate-700/70 rounded-xl p-5 shadow-sm space-y-4 flex flex-col justify-between">
        <div>
          <div class="flex items-center gap-2 border-b border-slate-100 dark:border-slate-800 pb-3">
            <div class="w-7 h-7 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
              <Icon icon="lucide:palette" :width="15" />
            </div>
            <div>
              <h3 class="text-sm font-bold text-slate-900 dark:text-slate-100">外观主题与系统信息</h3>
              <p class="text-[11px] text-slate-400">切换显示主题及查看当前平台版本</p>
            </div>
          </div>

          <div class="mt-4 space-y-4 text-xs">
            <div class="flex items-center justify-between bg-slate-50/80 dark:bg-slate-900/50 border border-slate-200/60 dark:border-slate-800 p-3 rounded-lg">
              <span class="font-bold text-slate-800 dark:text-slate-200">系统外观风格</span>
              <n-radio-group v-model:value="themeStore.theme" size="medium" @update:value="handleThemeChange">
                <n-radio-button value="dark">
                  <div class="flex items-center gap-1.5"><Icon icon="lucide:moon" :width="13" /> 深色模式</div>
                </n-radio-button>
                <n-radio-button value="light">
                  <div class="flex items-center gap-1.5"><Icon icon="lucide:sun" :width="13" /> 浅色模式</div>
                </n-radio-button>
              </n-radio-group>
            </div>

            <div class="bg-slate-50/80 dark:bg-slate-900/50 border border-slate-200/60 dark:border-slate-800 p-3 rounded-lg space-y-1.5">
              <div class="flex justify-between items-center text-[11.5px]">
                <span class="text-slate-400">系统内核版本</span>
                <span class="font-bold font-mono text-slate-800 dark:text-slate-200">v2.1.0 Enterprise</span>
              </div>
              <div class="flex justify-between items-center text-[11.5px] pt-1 border-t border-slate-200/40 dark:border-slate-800">
                <span class="text-slate-400">核心架构</span>
                <span class="font-mono text-slate-700 dark:text-slate-300">FastAPI + Vue3 + APScheduler</span>
              </div>
            </div>
          </div>
        </div>

        <p class="text-[11px] text-slate-400 dark:text-slate-500 pt-2 border-t border-slate-100 dark:border-slate-800">
          深浅双主题全面支持物理动效与视网膜高分屏自适应。
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
