import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  fetchDomainAlertSettings,
  saveDomainAlertSettings,
  testDomainAlertSettings,
} from '@/api'
import type { DomainAlertSettings, DomainAlertSettingsUpdate } from '@/api'

export const useSettingStore = defineStore('setting', () => {
  const domainAlertEnabled = ref(false)
  const reminderDays = ref(14)
  const warningDays = ref(7)
  const criticalDays = ref(3)
  const dingKeyword = ref('域名告警')
  const webhookConfigured = ref(false)
  const secretConfigured = ref(false)
  const loading = ref(false)
  const loaded = ref(false)
  const warningDaysThreshold = computed(() => reminderDays.value)

  function applySettings(settings: DomainAlertSettings) {
    domainAlertEnabled.value = settings.enabled
    reminderDays.value = settings.reminder_days
    warningDays.value = settings.warning_days
    criticalDays.value = settings.critical_days
    dingKeyword.value = settings.keyword
    webhookConfigured.value = settings.webhook_configured
    secretConfigured.value = settings.secret_configured
  }

  async function loadSettings() {
    if (loading.value) return
    loading.value = true
    try {
      applySettings(await fetchDomainAlertSettings())
      loaded.value = true
    } finally {
      loading.value = false
    }
  }

  async function updateDomainAlert(payload: DomainAlertSettingsUpdate) {
    applySettings(await saveDomainAlertSettings(payload))
  }

  async function testDomainAlert() {
    await testDomainAlertSettings()
  }

  return {
    domainAlertEnabled,
    reminderDays,
    warningDays,
    criticalDays,
    dingKeyword,
    warningDaysThreshold,
    webhookConfigured,
    secretConfigured,
    loading,
    loaded,
    loadSettings,
    updateDomainAlert,
    testDomainAlert,
  }
})
