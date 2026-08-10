import request from './request'
import type { ApiResponse, ResourceItem } from './types'

/** 获取指定账号和类型的云资源 */
export async function fetchResources(
  type: string,
  account?: string,
  account_id?: number | null
): Promise<ResourceItem[]> {
  const params: Record<string, any> = { type }
  if (account_id !== undefined && account_id !== null) {
    params.account_id = account_id
  } else if (account && account !== '全部账号') {
    params.account = account
  }
  const { data } = await request.get<ApiResponse<ResourceItem[]>>('/resources', { params })
  return data.data
}

/** 全局模糊搜索云资产 */
export async function searchResources(keyword: string, accountId?: number | null): Promise<ResourceItem[]> {
  const params: Record<string, any> = { keyword }
  if (accountId !== undefined && accountId !== null) params.account_id = accountId
  const { data } = await request.get<ApiResponse<ResourceItem[]>>('/search', {
    params,
  })
  return data.data
}

/** 检查本地数据库是否存有资产数据 */
export async function fetchDbStatus(): Promise<boolean> {
  const { data } = await request.get<{ status: string; is_empty: boolean }>('/db-status')
  return data.is_empty
}
