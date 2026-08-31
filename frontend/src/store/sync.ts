import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { triggerSync, fetchTaskStatus, syncSingleAccount } from '@/api'
import type { SyncTaskLog, TaskStatusType } from '@/api/types'
import { useResourceStore } from './resource'

export interface ActiveTaskInfo {
  taskId: string
  accountAlias: string
  accountId?: number
  startTime: string
  startTimestamp: number
  status: TaskStatusType
  errorCount: number
  elapsedSeconds: number
  lastBackendStatus?: string
  lastProgressSecond?: number
}

const ACTIVE_TASKS_KEY = 'aliyun-dashboard-active-tasks'
const SYNC_HISTORY_KEY = 'aliyun-dashboard-sync-history'
const MAX_EXECUTION_SECONDS = 900 // 15 分钟最大执行超时
const MAX_ERROR_COUNT = 5 // 连续失败 5 次终止跟踪

function appendResultDetails(log: SyncTaskLog, result: any) {
  if (!result || typeof result !== 'object') return

  if (typeof result.total === 'number') {
    log.logs.push(
      `[汇总] 账号总数 ${result.total}，成功 ${result.success_count || 0}，失败 ${result.failed_count || 0}，冷却跳过 ${result.skipped_cooldown_count || 0}，并发跳过 ${result.already_running_count || 0}`
    )
    const failed = Array.isArray(result.details?.failed) ? result.details.failed : []
    failed.forEach((item: any) => {
      const accountId = typeof item === 'object' ? item.account_id : item
      log.logs.push(`[账号 ${accountId}] ${item.status || '失败'}`)
      Object.entries(item.services || {}).forEach(([service, value]: [string, any]) => {
        log.logs.push(`  [${service}] ${value.status === 'success' ? `成功，资源 ${value.count || 0} 条` : `失败（${value.error_category || 'unknown'}）：${value.error || '未知错误'}`}`)
      })
    })
    return
  }

  if (result.account_id !== undefined) {
    log.logs.push(`[账号] ID ${result.account_id}`)
  }
  Object.entries(result.results || result.services || {}).forEach(([service, value]: [string, any]) => {
    log.logs.push(`[${service}] ${value.status === 'success' ? `成功，资源 ${value.count || 0} 条` : `失败（${value.error_category || 'unknown'}）：${value.error || '未知错误'}`}`)
  })
}

export const useSyncStore = defineStore('sync', () => {
  const resourceStore = useResourceStore()

  // 活动任务集字典 (以 taskId 为 key)
  const activeTasks = ref<Record<string, ActiveTaskInfo>>({})

  // 同步历史任务列表
  const syncHistory = ref<SyncTaskLog[]>([])

  // 全局唯一轮询定时器
  let globalPoller: ReturnType<typeof setInterval> | null = null

  // 计算属性：当前在跑的账号 ID 列表
  const syncingAccounts = computed<number[]>(() => {
    const ids: number[] = []
    Object.values(activeTasks.value).forEach(t => {
      if (t.accountId !== undefined && (t.status === 'pending' || t.status === 'running')) {
        ids.push(Number(t.accountId))
      }
    })
    return ids
  })

  // 计算属性：是否全量全局同步中
  const globalSyncing = computed<boolean>(() => {
    return Object.values(activeTasks.value).some(
      t => t.accountId === undefined && (t.status === 'pending' || t.status === 'running')
    )
  })

  // 计算属性：是否有任何任务正在进行
  const syncing = computed<boolean>(() => {
    return Object.values(activeTasks.value).some(
      t => t.status === 'pending' || t.status === 'running'
    )
  })

  const isSyncing = (id: number | string) => {
    const numericId = Number(id)
    return syncingAccounts.value.includes(numericId)
  }

  // 加载与保存活动任务
  function loadActiveTasks() {
    try {
      const raw = localStorage.getItem(ACTIVE_TASKS_KEY)
      if (raw) {
        activeTasks.value = JSON.parse(raw)
      }
    } catch (e) {
      console.error('Failed to load active tasks:', e)
    }
  }

  function saveActiveTasks() {
    try {
      localStorage.setItem(ACTIVE_TASKS_KEY, JSON.stringify(activeTasks.value))
    } catch (e) {
      console.error('Failed to save active tasks:', e)
    }
  }

  // 从 localStorage 恢复历史任务
  function loadHistory() {
    try {
      const raw = localStorage.getItem(SYNC_HISTORY_KEY)
      if (raw) {
        syncHistory.value = JSON.parse(raw)
      }
    } catch (e) {
      console.error('Failed to load sync history:', e)
    }
  }

  function saveHistory() {
    try {
      localStorage.setItem(SYNC_HISTORY_KEY, JSON.stringify(syncHistory.value.slice(0, 100)))
    } catch (e) {
      console.error('Failed to save sync history:', e)
    }
  }

  let isPolling = false

  // 启动统一公共轮询器
  function startGlobalPoller() {
    if (globalPoller) return

    globalPoller = setInterval(async () => {
      if (isPolling) return
      isPolling = true

      try {
        const activeTaskList = Object.values(activeTasks.value).filter(
          t => t.status === 'pending' || t.status === 'running'
        )

        if (activeTaskList.length === 0) {
          stopGlobalPoller()
          return
        }

        for (const task of activeTaskList) {
          const taskId = task.taskId
          const nowTime = new Date().toLocaleString('zh-CN', { hour12: false })
          
          // 1. 实时更新已用耗时
          task.elapsedSeconds = Math.floor((Date.now() - task.startTimestamp) / 1000)

          // 2. 检查最大超时时间 (15 分钟)
          if (task.elapsedSeconds > MAX_EXECUTION_SECONDS) {
            task.status = 'unknown'
            const currentLog = syncHistory.value.find(h => h.id === taskId)
            if (currentLog) {
              currentLog.status = 'unknown'
              currentLog.end_time = nowTime
              currentLog.duration = task.elapsedSeconds
              currentLog.logs.push(`[${nowTime}] ⏱️ 任务已超过 15 分钟前端跟踪上限，状态标记为【未知/超时未响应】，前端终止轮询（任务可能仍在后台进行）。`)
            }
            delete activeTasks.value[taskId]
            saveActiveTasks()
            saveHistory()
            continue
          }

          // 3. 轮询任务状态
          try {
            const res = await fetchTaskStatus(taskId, task.accountId)
            task.errorCount = 0 // 重置错误计数
            const currentLog = syncHistory.value.find(h => h.id === taskId)
            if (currentLog && res.task_status !== task.lastBackendStatus) {
              currentLog.logs.push(`[${nowTime}] [状态] 任务状态更新：${task.lastBackendStatus || 'PENDING'} → ${res.task_status}`)
              task.lastBackendStatus = res.task_status
            }

            if (res.task_status === 'SUCCESS') {
              let resultObj: any = res.result
              if (typeof res.result === 'string') {
                try { resultObj = JSON.parse(res.result) } catch (e) {}
              }
              if (currentLog) {
                currentLog.result = resultObj
                appendResultDetails(currentLog, resultObj)
              }

              if (resultObj && typeof resultObj === 'object' && resultObj.status === 'partial_failure') {
                task.status = 'partial_failure'
                if (currentLog) {
                  currentLog.status = 'partial_failure'
                  currentLog.end_time = nowTime
                  currentLog.duration = task.elapsedSeconds
                  currentLog.logs.push(`[${nowTime}] [完成] 同步结束，存在部分失败`)
                }
              } else if (resultObj && typeof resultObj === 'object' && resultObj.status === 'already_running') {
                task.status = 'already_running'
                if (currentLog) {
                  currentLog.status = 'already_running'
                  currentLog.end_time = nowTime
                  currentLog.logs.push(`[${nowTime}] [跳过] 账号已有任务在运行，本轮未重复执行`)
                }
              } else if (resultObj && typeof resultObj === 'object' && (resultObj.status === 'partial_success' || resultObj.status === 'completed_with_skips')) {
                task.status = resultObj.status
                if (currentLog) {
                  currentLog.status = resultObj.status
                  currentLog.end_time = nowTime
                  currentLog.duration = task.elapsedSeconds
                  currentLog.logs.push(`[${nowTime}] [完成] 部分账号因冷却或并发任务被跳过`)
                }
              } else {
                task.status = 'success'
                if (currentLog) {
                  currentLog.status = 'success'
                  currentLog.end_time = nowTime
                  currentLog.duration = task.elapsedSeconds
                  currentLog.logs.push(`[${nowTime}] [完成] 同步成功，总耗时 ${currentLog.duration} 秒`)
                }
              }

              delete activeTasks.value[taskId]
              saveActiveTasks()
              saveHistory()

              // 静默拉取最新资源列表
              await resourceStore.loadAllResources()
            } else if (res.task_status === 'FAILURE') {
              task.status = 'failure'
              if (currentLog) {
                currentLog.status = 'failure'
                currentLog.end_time = nowTime
                currentLog.duration = task.elapsedSeconds
                if (res.result) {
                  currentLog.logs.push(`[错误] ${typeof res.result === 'object' ? JSON.stringify(res.result) : res.result}`)
                }
                if (res.traceback) {
                  currentLog.logs.push(`[错误堆栈]`)
                  res.traceback.split('\n').forEach(line => {
                    if (line.trim()) {
                      currentLog.logs.push(`  ${line}`)
                    }
                  })
                }
                currentLog.logs.push(`[${nowTime}] [失败] 同步任务异常中断`)
              }
              delete activeTasks.value[taskId]
              saveActiveTasks()
              saveHistory()
            } else {
              // 处于 PENDING 或 STARTED 正常轮询中
              if (currentLog && task.elapsedSeconds - (task.lastProgressSecond || 0) >= 10) {
                task.lastProgressSecond = task.elapsedSeconds
                currentLog.logs.push(`[${nowTime}] [进度] 正在拉取云资产，已耗时 ${task.elapsedSeconds} 秒`)
                saveHistory()
              }
            }
          } catch (err) {
            task.errorCount++
            console.error(`Polling status error for task ${taskId} (error count ${task.errorCount}):`, err)
            
            if (task.errorCount >= MAX_ERROR_COUNT) {
              task.status = 'unknown'
              const currentLog = syncHistory.value.find(h => h.id === taskId)
              if (currentLog) {
                currentLog.status = 'unknown'
                currentLog.end_time = nowTime
                currentLog.duration = task.elapsedSeconds
                currentLog.logs.push(`[${nowTime}] ⚠️ 连续 ${MAX_ERROR_COUNT} 次轮询接口失败，已自动停止追踪该任务。`)
              }
              delete activeTasks.value[taskId]
              saveActiveTasks()
              saveHistory()
            }
          }
        } // end of for-loop
      } finally {
        isPolling = false
      }
    }, 2000)
  }

  function stopGlobalPoller() {
    if (globalPoller) {
      clearInterval(globalPoller)
      globalPoller = null
    }
  }

  const syncTimeElapsed = computed(() => {
    const activeList = Object.values(activeTasks.value)
    if (activeList.length === 0) return 0
    return Math.max(...activeList.map(t => t.elapsedSeconds))
  })

  // 注册并追踪新任务
  function trackSyncTask(taskId: string, accountAlias = '全局全量同步', accountId?: number) {
    if (!taskId) return
    if (activeTasks.value[taskId] || syncHistory.value.some(h => h.id === taskId)) return

    const nowTimestamp = Date.now()
    const startTimeStr = new Date(nowTimestamp).toLocaleString('zh-CN', { hour12: false })

    const activeTask: ActiveTaskInfo = {
      taskId,
      accountAlias,
      accountId,
      startTime: startTimeStr,
      startTimestamp: nowTimestamp,
      status: 'running',
      errorCount: 0,
      elapsedSeconds: 0,
      lastBackendStatus: 'PENDING',
      lastProgressSecond: 0,
    }

    activeTasks.value[taskId] = activeTask
    saveActiveTasks()

    // 写入历史日志记录
    const taskLog: SyncTaskLog = {
      id: taskId,
      account_alias: accountAlias,
      account_id: accountId,
      start_time: startTimeStr,
      end_time: null,
      duration: 0,
      status: 'running',
      logs: [
        `[${startTimeStr}] [创建] 任务 ID：${taskId}`,
        `[${startTimeStr}] [范围] ${accountId === undefined ? '全部云账号' : `账号 ${accountAlias}（ID ${accountId}）`}`,
        `[${startTimeStr}] [调度] 已启动后台轻量异步任务执行`,
      ]
    }
    syncHistory.value.unshift(taskLog)
    saveHistory()

    startGlobalPoller()
  }

  // 触发全局全量同步
  async function triggerGlobalSync() {
    try {
      const res = await triggerSync()
      if (res && res.task_id) {
        trackSyncTask(res.task_id, '全局全量同步')
      }
      return res
    } catch (e) {
      console.error('Failed to trigger global sync:', e)
      throw e
    }
  }

  // 触发单账号同步
  async function triggerSingleAccountSync(id: number | string, accountAlias: string) {
    const numericId = Number(id)
    try {
      const res = await syncSingleAccount(numericId)
      if (res && res.status === 'already_running') {
        console.warn(`Account ${accountAlias} is already running in task ${res.task_id}`)
        return res
      }
      if (res && res.task_id) {
        trackSyncTask(res.task_id, accountAlias, numericId)
      }
      return res
    } catch (e) {
      console.error(`Failed to trigger sync for account ${id}:`, e)
      throw e
    }
  }

  function stopTracking() {
    stopGlobalPoller()
    activeTasks.value = {}
    saveActiveTasks()
  }

  function removeHistory(taskId: string): boolean {
    if (activeTasks.value[taskId]) return false
    syncHistory.value = syncHistory.value.filter(item => item.id !== taskId)
    saveHistory()
    return true
  }

  function clearHistory(): number {
    const activeIds = new Set(Object.keys(activeTasks.value))
    const before = syncHistory.value.length
    syncHistory.value = syncHistory.value.filter(item => activeIds.has(item.id))
    saveHistory()
    return before - syncHistory.value.length
  }

  // 初始化：自动恢复页面刷新前的未完成任务
  loadHistory()
  loadActiveTasks()
  if (Object.values(activeTasks.value).some(t => t.status === 'pending' || t.status === 'running')) {
    startGlobalPoller()
  }

  return {
    activeTasks,
    syncing,
    globalSyncing,
    syncingAccounts,
    syncHistory,
    syncTimeElapsed,
    isSyncing,
    loadHistory,
    trackSyncTask,
    triggerGlobalSync,
    triggerSingleAccountSync,
    stopTracking,
    removeHistory,
    clearHistory,
  }
})
