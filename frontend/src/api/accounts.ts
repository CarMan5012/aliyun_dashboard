import request from './request'
import type { ApiResponse, CloudAccountItem, SyncSubmitResponse, AccountSaveResponse } from './types'

/** 获取所有云账号的详细列表 */
export async function fetchAccountsFull(): Promise<CloudAccountItem[]> {
  const { data } = await request.get<ApiResponse<CloudAccountItem[]>>('/accounts')
  return data.data
}

/** 新增云账号 */
export async function createAccount(
  alias: string,
  ak: string,
  sk: string,
  interval: number
): Promise<AccountSaveResponse> {
  const { data } = await request.post<AccountSaveResponse>('/accounts', {
    account_alias: alias,
    access_key_id: ak,
    access_key_secret: sk,
    sync_interval: interval,
  })
  return data
}

/** 更新云账号 */
export async function updateAccountApi(
  id: number,
  payload: {
    account_alias?: string
    access_key_id?: string
    access_key_secret?: string
    sync_interval?: number
  }
): Promise<AccountSaveResponse> {
  const { data } = await request.put<AccountSaveResponse>(`/accounts/${id}`, payload)
  return data
}

/** 删除云账号 */
export async function deleteAccount(id: number): Promise<void> {
  await request.delete(`/accounts/${id}`)
}

/** 手动触发单个账号的资产同步 */
export async function syncSingleAccount(id: number): Promise<SyncSubmitResponse> {
  const { data } = await request.post<SyncSubmitResponse>(`/accounts/${id}/sync`)
  return data
}
