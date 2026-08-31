import { defineStore } from 'pinia'
import { computed } from 'vue'
import { useResourceStore } from './resource'
import { useSettingStore } from './setting'
import dayjs from 'dayjs'

export const useNotificationStore = defineStore('notification', () => {
  const resourceStore = useResourceStore()
  const settingStore = useSettingStore()

  // 1. 到期域名提醒列表（包含临期及已逾期30天内的紧急域名）
  const warningDomains = computed(() => {
    const threshold = settingStore.reminderDays
    const today = dayjs().startOf('day')
    return resourceStore.domainList.filter((d) => {
      const expDate = d.details.expiration_date
      if (!expDate) return false
      const target = dayjs(expDate).startOf('day')
      const days = target.diff(today, 'day')
      return days <= threshold && days >= -30
    })
  })

  // 2. 到期证书提醒列表（包含临期及已逾期30天内的紧急证书）
  const warningCerts = computed(() => {
    const threshold = settingStore.warningDaysThreshold
    const today = dayjs().startOf('day')
    return resourceStore.sslList.filter((c) => {
      const endTime = c.details.cert_end_time
      if (!endTime) return false
      const target = dayjs(endTime).startOf('day')
      const days = target.diff(today, 'day')
      return days <= threshold && days >= -30
    })
  })

  // 3. 总提醒消息数
  const unreadCount = computed(() => {
    return warningDomains.value.length + warningCerts.value.length
  })

  return {
    warningDomains,
    warningCerts,
    unreadCount,
  }
})
