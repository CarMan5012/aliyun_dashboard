<template>
  <div class="space-y-4">
        <!-- 头部 -->
        <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white/90 dark:bg-cardDark/90 border border-slate-200/80 dark:border-slate-700/70 px-4 py-3.5 rounded-lg shadow-sm">
          <div>
            <div class="flex items-center gap-2">
              <h1 class="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">系统配置中心</h1>
            </div>
            <p class="mt-0.5 text-xs leading-4 text-slate-500 dark:text-slate-400 font-medium">
              配置全局过期报警警报以及云资产自动同步策略
            </p>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- 域名钉钉告警 -->
          <section class="md:col-span-2 overflow-hidden bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl shadow-sm">
            <header class="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between px-5 py-3.5 border-b border-borderLight dark:border-borderDark bg-slate-50/40 dark:bg-slate-900/20">
              <div class="flex items-center gap-3">
                <div class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-600 dark:bg-blue-950/50 dark:text-blue-400">
                  <Icon icon="lucide:bell-ring" :width="15" />
                </div>
                <div>
                  <h3 class="text-sm font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-2">
                    域名到期钉钉告警
                    <span v-if="settingStore.loaded" class="inline-flex items-center gap-1.5 text-[11px] font-normal text-slate-500">
                      <span class="h-1.5 w-1.5 rounded-full" :class="settingStore.domainAlertEnabled ? 'bg-emerald-500' : 'bg-slate-300 dark:bg-slate-600'" />
                      {{ settingStore.domainAlertEnabled ? '运行中' : '已停用' }}
                    </span>
                  </h3>
                  <p class="text-[11px] text-slate-400 dark:text-slate-500">
                    域名首次进入提醒/告警/严重等级时推送告警；休息日首次告警将在下个工作日补发。
                  </p>
                </div>
              </div>
            </header>

            <div v-if="settingStore.loaded && credentialsLoaded" class="text-xs">
              <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px]">
                <!-- 左侧：通知通道 -->
                <section class="p-4 space-y-3.5">
                  <div class="flex items-center justify-between">
                    <h4 class="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                      <Icon icon="lucide:send" :width="13" class="text-slate-400" />
                      通知通道设置
                    </h4>
                    <span class="text-[11px]" :class="settingStore.webhookConfigured ? 'text-emerald-600 dark:text-emerald-400 font-medium' : 'text-slate-400'">
                      {{ settingStore.webhookConfigured ? '● Webhook 已就绪' : '○ 未配置 Webhook' }}
                    </span>
                  </div>

                  <div class="space-y-1.5">
                    <label class="text-[11px] font-medium text-slate-600 dark:text-slate-300">钉钉 Webhook</label>
                    <n-input
                      v-model:value="webhook"
                      type="password"
                      size="small"
                      show-password-on="click"
                      :placeholder="settingStore.webhookConfigured ? 'Webhook 已保存；输入新值可替换' : '请输入钉钉机器人 Webhook 地址'"
                    />
                  </div>

                  <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div class="space-y-1.5">
                      <label class="text-[11px] font-medium text-slate-600 dark:text-slate-300">自定义关键词 (可选)</label>
                      <n-input
                        v-model:value="settingStore.dingKeyword"
                        maxlength="100"
                        size="small"
                        placeholder="钉钉安全设置的自定义关键词"
                      />
                    </div>

                    <div class="space-y-1.5">
                      <div class="flex items-center justify-between">
                        <label class="text-[11px] font-medium text-slate-600 dark:text-slate-300">加签 Secret (可选)</label>
                        <span class="text-[10px]" :class="settingStore.secretConfigured ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400'">
                          {{ settingStore.secretConfigured ? '已配置' : '未配置' }}
                        </span>
                      </div>
                      <n-input
                        v-model:value="dingSecret"
                        type="password"
                        size="small"
                        show-password-on="click"
                        :placeholder="settingStore.secretConfigured ? 'Secret 已保存；输入新值替换' : '加签 Secret 密钥'"
                      />
                    </div>
                  </div>
                </section>

                <!-- 右侧：告警规则及天数 -->
                <section class="border-t xl:border-t-0 xl:border-l border-borderLight dark:border-borderDark bg-slate-50/60 dark:bg-slate-900/30 p-4 flex flex-col justify-between space-y-3">
                  <div>
                    <div class="flex items-center justify-between gap-3 mb-3">
                      <div>
                        <h4 class="text-xs font-bold text-slate-800 dark:text-slate-200">告警规则开关</h4>
                        <p class="text-[11px] text-slate-400">按剩余天数分级提醒</p>
                      </div>
                      <n-switch v-model:value="settingStore.domainAlertEnabled" size="small" />
                    </div>

                    <div class="space-y-2">
                      <div class="flex items-center justify-between gap-3 rounded-lg border border-borderLight dark:border-borderDark bg-white dark:bg-slate-900/50 px-3 py-2">
                        <div class="flex items-center gap-2">
                          <span class="h-2 w-2 rounded-full bg-blue-500" />
                          <span class="text-xs font-semibold text-slate-700 dark:text-slate-300">提醒天数</span>
                        </div>
                        <n-input-number v-model:value="settingStore.reminderDays" :min="1" :max="365" size="small" :show-button="false" class="w-20">
                          <template #suffix>天</template>
                        </n-input-number>
                      </div>
                      <div class="flex items-center justify-between gap-3 rounded-lg border border-borderLight dark:border-borderDark bg-white dark:bg-slate-900/50 px-3 py-2">
                        <div class="flex items-center gap-2">
                          <span class="h-2 w-2 rounded-full bg-amber-500" />
                          <span class="text-xs font-semibold text-slate-700 dark:text-slate-300">告警天数</span>
                        </div>
                        <n-input-number v-model:value="settingStore.warningDays" :min="1" :max="365" size="small" :show-button="false" class="w-20">
                          <template #suffix>天</template>
                        </n-input-number>
                      </div>
                      <div class="flex items-center justify-between gap-3 rounded-lg border border-borderLight dark:border-borderDark bg-white dark:bg-slate-900/50 px-3 py-2">
                        <div class="flex items-center gap-2">
                          <span class="h-2 w-2 rounded-full bg-rose-500" />
                          <span class="text-xs font-semibold text-slate-700 dark:text-slate-300">严重天数</span>
                        </div>
                        <n-input-number v-model:value="settingStore.criticalDays" :min="0" :max="365" size="small" :show-button="false" class="w-20">
                          <template #suffix>天</template>
                        </n-input-number>
                      </div>
                    </div>
                  </div>

                  <p class="text-[10.5px] text-slate-400 dark:text-slate-500">提醒天数 &gt; 告警天数 &gt; 严重天数</p>
                </section>
              </div>

              <footer class="flex items-center justify-between px-4 py-2.5 border-t border-borderLight dark:border-borderDark bg-slate-50/30 dark:bg-cardDark">
                <span class="text-[11px] text-slate-400 dark:text-slate-500">保存后自动触发即时检查。</span>
                <div class="flex items-center gap-2">
                  <n-button size="small" :loading="testing" @click="testDomainAlert">发送测试消息</n-button>
                  <n-button size="small" type="primary" :loading="saving" @click="saveDomainAlert">保存配置</n-button>
                </div>
              </footer>
            </div>
            <div v-else class="py-8 text-center text-xs text-slate-400">
              正在加载告警配置...
            </div>
          </section>

          <!-- 自动同步设置 (基于各个账号配置) -->
          <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 space-y-4 shadow-sm">
            <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5 uppercase tracking-wider border-b border-borderLight dark:border-borderDark pb-2">
              <Icon icon="lucide:refresh-cw" :width="14" />
              云账号数据同步周期
            </h3>
            <div class="space-y-4 text-xs">
              <p class="text-slate-500 dark:text-slate-450">更改各个托管云账号的自动拉取时间周期（通过系统内置定时调度器分发）。</p>
              <div class="space-y-3 max-h-[160px] overflow-y-auto pr-1 custom-scroll">
                <div v-for="acc in accountStore.accounts" :key="acc.id" class="flex justify-between items-center bg-slate-50 dark:bg-slate-900/50 border border-borderLight dark:border-borderDark p-3 rounded-xl">
                  <span class="font-semibold text-slate-700 dark:text-slate-300">{{ acc.account_alias }}</span>
                  <n-select
                    v-model:value="acc.sync_interval"
                    :options="intervalOptions"
                    style="width: 160px"
                    @update:value="(val: any) => handleIntervalChange(acc.id, val)"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 界面主题配置 -->
          <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 space-y-4 shadow-sm">
            <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5 uppercase tracking-wider border-b border-borderLight dark:border-borderDark pb-2">
              <Icon icon="lucide:palette" :width="14" />
              界面主题配置
            </h3>
            <div class="space-y-4 text-xs">
              <p class="text-slate-500 dark:text-slate-450">切换系统的显示主题风格，提供深色与浅色两套独立配色系统。</p>
              <div class="flex items-center gap-4">
                <span class="text-slate-700 dark:text-slate-350 font-semibold">系统显示主题</span>
                <n-radio-group v-model:value="themeStore.theme" name="theme-group" @update:value="handleThemeChange">
                  <n-radio-button value="dark">
                    <div class="flex items-center gap-1"><Icon icon="lucide:moon" :width="12" /> 深色模式</div>
                  </n-radio-button>
                  <n-radio-button value="light">
                    <div class="flex items-center gap-1"><Icon icon="lucide:sun" :width="12" /> 浅色模式</div>
                  </n-radio-button>
                </n-radio-group>
              </div>
            </div>
          </div>

          <!-- 系统内核与版本配置面板 -->
          <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 space-y-4 shadow-sm">
            <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5 uppercase tracking-wider border-b border-borderLight dark:border-borderDark pb-2">
              <Icon icon="lucide:info" :width="14" />
              系统版本与关于
            </h3>
            <div class="space-y-3 text-xs">
              <p class="text-slate-500 dark:text-slate-450">当前平台的开发与运行环境版本信息如下：</p>
              <div class="space-y-2 bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-borderLight dark:border-borderDark">
                <div class="flex justify-between items-center py-1">
                  <span class="text-slate-450 dark:text-slate-500">平台系统版本</span>
                  <span class="font-bold text-slate-700 dark:text-slate-300">v2.1.0 (Enterprise Build)</span>
                </div>
                <div class="flex justify-between items-center py-1 border-t border-borderLight dark:border-borderDark">
                  <span class="text-slate-450 dark:text-slate-500">前端框架版本</span>
                  <span class="font-mono text-slate-700 dark:text-slate-300">Vue 3.4.0 + NaiveUI 2.38</span>
                </div>
                <div class="flex justify-between items-center py-1 border-t border-borderLight dark:border-borderDark">
                  <span class="text-slate-450 dark:text-slate-500">后端服务版本</span>
                  <span class="font-mono text-slate-700 dark:text-slate-300">FastAPI 0.110 + Python 3.10</span>
                </div>
                <div class="flex justify-between items-center py-1 border-t border-borderLight dark:border-borderDark">
                  <span class="text-slate-450 dark:text-slate-500">数据库及中间件</span>
                  <span class="font-mono text-slate-700 dark:text-slate-300">MySQL 8.0 + Redis 7.2</span>
                </div>
              </div>
            </div>
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
  { label: '手动同步 (不自动)', value: 0 },
  { label: '每 1 小时同步', value: 1 },
  { label: '每 6 小时同步', value: 6 },
  { label: '每 12 小时同步', value: 12 },
  { label: '每天自动同步', value: 24 },
]

function apiError(error: any): string {
  return error?.response?.data?.detail || error?.message || '操作失败'
}

async function saveDomainAlert() {
  if (!settingStore.dingKeyword.trim()) {
    message.warning('请输入钉钉自定义关键词')
    return
  }
  if (!(settingStore.reminderDays > settingStore.warningDays && settingStore.warningDays > settingStore.criticalDays)) {
    message.warning('阈值必须满足：提醒天数 > 告警天数 > 严重天数')
    return
  }
  saving.value = true
  try {
    await settingStore.updateDomainAlert({
      enabled: settingStore.domainAlertEnabled,
      reminder_days: settingStore.reminderDays,
      warning_days: settingStore.warningDays,
      critical_days: settingStore.criticalDays,
      keyword: settingStore.dingKeyword.trim(),
      ...(webhook.value.trim() ? { webhook: webhook.value.trim() } : {}),
      ...(dingSecret.value.trim() ? { secret: dingSecret.value.trim() } : {}),
    })
    message.success('域名钉钉告警配置已保存')
  } catch (error) {
    message.error(apiError(error))
  } finally {
    saving.value = false
  }
}

async function revealCredentials() {
  try {
    const credentials = await fetchDomainAlertCredentials()
    webhook.value = credentials.webhook || ''
    dingSecret.value = credentials.secret || ''
    credentialsLoaded.value = true
  } catch (error: any) {
    // 即使凭据获取遇到错误，也允许界面渲染，以便用户可以重新配置
    credentialsLoaded.value = true
    const status = error?.response?.status
    if (status === 403) {
      message.warning('当前服务端已配置设置管理口令，请输入口令后再进行操作')
    } else {
      console.warn('获取既有告警凭据失败:', error)
    }
  }
}

async function testDomainAlert() {
  testing.value = true
  try {
    await settingStore.testDomainAlert()
    message.success('钉钉测试消息已发送')
  } catch (error) {
    message.error(apiError(error))
  } finally {
    testing.value = false
  }
}

async function handleIntervalChange(id: number, val: number) {
  try {
    await accountStore.updateAccount(id, { sync_interval: val })
    message.success('已修改同步自动周期')
  } catch (e) {
    message.error('修改同步周期失败')
    await accountStore.loadAccounts()
  }
}

function handleThemeChange(val: 'light' | 'dark') {
  themeStore.theme = val
  localStorage.setItem('aliyun-dashboard-theme', val)
  message.success(`主题已成功切换为 ${val === 'dark' ? '深色模式' : '浅色模式'}`)
}
</script>

<style scoped>
.setting-section {
  transition: transform 160ms cubic-bezier(0.23, 1, 0.32, 1), box-shadow 160ms ease;
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
