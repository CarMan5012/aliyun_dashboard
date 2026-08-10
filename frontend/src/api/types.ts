export interface ResourceItem {
  id: number
  account_id?: number
  account_name: string
  resource_type: 'ECS' | 'EIP' | 'Domain' | 'SSL'
  search_key: string | null
  update_time: string | null
  details: Record<string, any>
}

export interface ApiResponse<T = any> {
  status: string
  data: T
  message?: string
}

export interface DbStatusResponse {
  status: string
  is_empty: boolean
}

export interface CloudAccountItem {
  id: number
  account_alias: string
  access_key_id: string
  sync_interval: number
  last_synced_at?: string
  last_attempted_at?: string
  last_sync_status: 'never' | 'success' | 'partial_failure' | 'failure'
  last_sync_error?: string | null
  last_sync_details?: Record<string, { status: string; count?: number; error?: string; error_category?: string }> | null
  active_regions?: string[]
  created_at?: string
  updated_at?: string
}

export interface AccountSaveResponse {
  status: string
  data: CloudAccountItem
  sync_queued: boolean
  task_id?: string | null
  warning?: string | null
}

export interface SyncSubmitResponse {
  status: string
  task_id: string
  message: string
}

export interface TaskResultDetails {
  success?: any[]
  failed?: any[]
  skipped_cooldown?: any[]
  already_running?: any[]
}

export interface TaskResult {
  status?: 'success' | 'partial_failure' | 'partial_success' | 'completed_with_skips' | 'already_running'
  total?: number
  success_count?: number
  failed_count?: number
  skipped_cooldown_count?: number
  already_running_count?: number
  details?: TaskResultDetails
  message?: string
  task_id?: string
}

export type TaskStatusType = 'pending' | 'running' | 'success' | 'failure' | 'unknown' | 'partial_failure' | 'partial_success' | 'completed_with_skips' | 'already_running'

export interface TaskStatusResponse {
  status: string
  task_id: string
  task_status: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE' | string
  ready: boolean
  result: string | TaskResult | null
  traceback?: string | null
}

export interface SyncTaskLog {
  id: string
  account_alias: string
  account_id?: number
  start_time: string
  end_time: string | null
  duration: number
  status: TaskStatusType
  logs: string[]
  result?: TaskResult | Record<string, any> | null
}
