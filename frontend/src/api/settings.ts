import request from './request'

export interface DomainAlertSettings {
  enabled: boolean
  reminder_days: number
  warning_days: number
  critical_days: number
  keyword: string
  webhook_configured: boolean
  secret_configured: boolean
}

export interface DomainAlertSettingsUpdate {
  enabled: boolean
  reminder_days: number
  warning_days: number
  critical_days: number
  keyword: string
  webhook?: string
  secret?: string
}

export interface DomainAlertCredentials {
  webhook: string | null
  secret: string | null
}

export async function fetchDomainAlertSettings(): Promise<DomainAlertSettings> {
  const { data } = await request.get('/settings/domain-alert')
  return data.data
}

export async function saveDomainAlertSettings(
  payload: DomainAlertSettingsUpdate
): Promise<DomainAlertSettings> {
  const { data } = await request.put('/settings/domain-alert', payload)
  return data.data
}

export async function fetchDomainAlertCredentials(): Promise<DomainAlertCredentials> {
  const { data } = await request.get('/settings/domain-alert/credentials')
  return data.data
}

export async function testDomainAlertSettings(): Promise<void> {
  await request.post('/settings/domain-alert/test')
}
