import request from './request'
import type { SyncSubmitResponse, TaskStatusResponse } from './types'

/** 手动触发全量账号资源同步 */
export async function triggerSync(): Promise<SyncSubmitResponse> {
  const { data } = await request.post<SyncSubmitResponse>('/sync')
  return data
}

/** 查询 Celery 异步同步任务的执行状态 */
export async function fetchTaskStatus(taskId: string): Promise<TaskStatusResponse> {
  const { data } = await request.get<TaskStatusResponse>(`/tasks/${taskId}`)
  return data
}
