<template>
  <div class="space-y-4">
    <!-- 头部标题 Banner -->
    <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white/90 dark:bg-cardDark/90 border border-slate-200/80 dark:border-slate-700/70 px-4 py-3.5 rounded-lg shadow-sm">
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-lg font-bold tracking-tight text-slate-900 dark:text-slate-100">同步任务中心</h1>
        </div>
        <p class="mt-0.5 text-xs leading-4 text-slate-500 dark:text-slate-400 font-medium">
          查看与控制云资产拉取任务
        </p>
      </div>
      <div class="flex items-center gap-2 mt-2 sm:mt-0">
        <n-button size="medium" secondary :disabled="syncStore.syncHistory.length === 0" @click="handleClearHistory">
          清空完成日志
        </n-button>
        <n-button type="primary" size="medium" :loading="syncStore.globalSyncing" @click="handleForceSync">
          立即触发同步
        </n-button>
      </div>
    </div>

    <!-- 任务列表与日志区 (3/5 + 2/5) -->
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-5">
      <!-- 左侧 3/5：任务流水表 -->
      <div class="lg:col-span-3 animate-fade-in">

          <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-3.5 shadow-sm">
            <n-data-table
              class="sync-table"
              size="medium"
              :columns="columns"
              :data="syncStore.syncHistory"
              :row-key="(row: any) => row.id"
              :pagination="{ pageSize: 10 }"
              :striped="false"
            />
          </div>
        </div>

        <!-- 右侧 2/5：日志详情区 -->
        <div class="lg:col-span-2 bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-4 flex flex-col justify-between shadow-sm">
          <div>
            <h3 class="text-sm font-semibold text-slate-500 dark:text-slate-400 flex items-center gap-1.5 uppercase tracking-wider mb-3 border-b border-borderLight dark:border-borderDark pb-2">
              <Icon icon="lucide:terminal" :width="14" />
              任务执行日志
            </h3>
            <div v-if="!selectedTask" class="text-xs text-slate-400 dark:text-slate-500 text-center py-20">
              请点击任务行查看具体执行日志
            </div>
            <div v-else class="space-y-3">
              <div class="grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11.5px] bg-slate-50/80 dark:bg-slate-900/50 p-3 rounded-lg border border-borderLight dark:border-borderDark">
                <p class="col-span-2 min-w-0"><span class="text-slate-400 dark:text-slate-500">任务 ID：</span><span class="font-mono text-slate-700 dark:text-slate-300 break-all text-[11px]">{{ selectedTask.id }}</span></p>
                <p><span class="text-slate-400 dark:text-slate-500">执行范围：</span><span class="font-semibold text-primary">{{ selectedTask.account_alias }}</span></p>
                <p><span class="text-slate-400 dark:text-slate-500">状态：</span><span class="font-semibold" :class="[selectedTask.status === 'success' ? 'text-success' : selectedTask.status === 'failure' ? 'text-danger' : ['partial_failure', 'partial_success', 'completed_with_skips'].includes(selectedTask.status) ? 'text-warning' : selectedTask.status === 'unknown' ? 'text-slate-500' : 'text-primary animate-pulse']">{{ getStatusLabel(selectedTask.status) }}</span></p>
                <p><span class="text-slate-400 dark:text-slate-500">开始：</span><span class="font-mono text-[11px]">{{ selectedTask.start_time }}</span></p>
                <p><span class="text-slate-400 dark:text-slate-500">结束：</span><span class="font-mono text-[11px]">{{ selectedTask.end_time || '-' }}</span></p>
                <p><span class="text-slate-400 dark:text-slate-500">耗时：</span><span class="font-mono text-[11px]">{{ selectedTask.duration ? `${selectedTask.duration} 秒` : '-' }}</span></p>
                <p><span class="text-slate-400 dark:text-slate-500">日志：</span><span class="font-medium">{{ selectedTask.logs.length }} 条</span></p>
              </div>

              <!-- 终端日志内容 -->
              <div class="bg-slate-950 border border-borderLight dark:border-borderDark rounded-lg p-3 font-mono text-[11px] text-slate-300 space-y-1.5 h-[410px] overflow-y-auto custom-scroll leading-relaxed select-text">
                <p v-for="(log, idx) in selectedTask.logs" :key="idx" class="whitespace-pre-wrap break-words" :class="getLogClass(log)">{{ log }}</p>
              </div>
            </div>
          </div>

          <!-- 手动重试 -->
          <div v-if="selectedTask && selectedTask.status === 'failure'" class="mt-3 pt-3 border-t border-borderLight dark:border-borderDark">
            <n-button type="warning" class="w-full" size="small" @click="handleRetry(selectedTask)">
              一键重试此任务
            </n-button>
          </div>
        </div>
      </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import { NButton, NTag, useMessage } from 'naive-ui'
import { useSyncStore } from '@/store'
import type { SyncTaskLog } from '@/api'

const syncStore = useSyncStore()
const message = useMessage()

const selectedTaskId = ref<string | null>(null)

const selectedTask = computed(() => {
  if (!selectedTaskId.value && syncStore.syncHistory.length > 0) {
    return syncStore.syncHistory[0]
  }
  return syncStore.syncHistory.find((t) => t.id === selectedTaskId.value) || null
})

onMounted(() => {
  syncStore.loadHistory()
  if (syncStore.syncHistory.length > 0) {
    selectedTaskId.value = syncStore.syncHistory[0].id
  }
})

async function handleForceSync() {
  try {
    const res = await syncStore.triggerGlobalSync()
    selectedTaskId.value = res.task_id
    message.success('已触发全局资产同步')
  } catch (e) {
    message.error('同步失败')
  }
}

async function handleRetry(task: SyncTaskLog) {
  try {
    message.info(`正在重试同步：${task.account_alias}`)
    if (task.account_alias === '全局全量同步') {
      const res = await syncStore.triggerGlobalSync()
      selectedTaskId.value = res.task_id
    } else {
      message.warning('重试非全局任务建议在账号管理页点击"立即同步"')
    }
  } catch (e) {
    message.error('重试失败')
  }
}

function handleDeleteHistory(task: SyncTaskLog) {
  if (syncStore.activeTasks[task.id]) {
    message.warning('运行中的任务日志不能删除')
    return
  }
  if (!window.confirm(`确认删除任务 ${task.id.substring(0, 8)} 的操作日志？`)) return
  syncStore.removeHistory(task.id)
  selectedTaskId.value = syncStore.syncHistory[0]?.id || null
  message.success('操作日志已删除')
}

function handleClearHistory() {
  if (!window.confirm('确认清空全部已完成的同步操作日志？运行中的日志会保留。')) return
  const count = syncStore.clearHistory()
  selectedTaskId.value = syncStore.syncHistory[0]?.id || null
  message.success(`已删除 ${count} 条操作日志`)
}

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    pending: '等待中',
    running: '执行中',
    success: '成功',
    failure: '失败',
    partial_failure: '部分失败',
    partial_success: '部分完成',
    completed_with_skips: '完成有跳过',
    already_running: '并发跳过',
    unknown: '状态未知',
  }
  return labels[status] || status
}

function getLogClass(log: string): string {
  if (log.includes('[失败]') || log.includes('[错误]')) return 'text-red-400'
  if (log.includes('[完成]') || log.includes('成功，资源')) return 'text-emerald-400'
  if (log.includes('[跳过]') || log.includes('部分失败')) return 'text-amber-400'
  if (log.includes('[状态]') || log.includes('[进度]')) return 'text-sky-400'
  return ''
}

const columns = [
  {
    title: '任务 ID',
    key: 'id',
    render(row: SyncTaskLog) {
      return h('span', {
        class: 'font-mono text-[11.5px] cursor-pointer text-primary hover:underline font-medium',
        onClick: () => { selectedTaskId.value = row.id }
      }, row.id.substring(0, 8) + '...')
    }
  },
  {
    title: '云账号',
    key: 'account_alias',
    render(row: SyncTaskLog) {
      return h('span', { class: 'font-semibold text-[12px] text-slate-700 dark:text-slate-200' }, row.account_alias)
    }
  },
  { title: '开始时间', key: 'start_time', render(row: SyncTaskLog) { return h('span', { class: 'font-mono text-[11.5px] text-slate-600 dark:text-slate-300' }, row.start_time) } },
  { title: '耗时', key: 'duration', render(row: SyncTaskLog) { return h('span', { class: 'text-[11.5px] text-slate-600 dark:text-slate-300 font-medium' }, row.duration ? `${row.duration} 秒` : '-') } },
  {
    title: '状态',
    key: 'status',
    render(row: SyncTaskLog) {
      let type: 'success' | 'warning' | 'error' | 'info' | 'default' = 'info'
      let label = '执行中'
      if (row.status === 'success') {
        type = 'success'
        label = '成功'
      } else if (row.status === 'failure') {
        type = 'error'
        label = '失败'
      } else if (row.status === 'partial_failure') {
        type = 'warning'
        label = '部分失败'
      } else if (row.status === 'partial_success') {
        type = 'warning'
        label = '部分完成'
      } else if (row.status === 'completed_with_skips') {
        type = 'warning'
        label = '完成有跳过'
      } else if (row.status === 'already_running') {
        type = 'info'
        label = '并发跳过'
      } else if (row.status === 'unknown') {
        type = 'default'
        label = '状态未知'
      }
      return h(NTag, { size: 'small', type, bordered: false }, { default: () => label })
    }
  },
  {
    title: '操作',
    key: 'action',
    render(row: SyncTaskLog) {
      return h('div', { class: 'flex items-center gap-1' }, [
        h(NButton, {
          size: 'tiny',
          quaternary: true,
          type: 'primary',
          onClick: () => { selectedTaskId.value = row.id }
        }, { default: () => '详情' }),
        h(NButton, {
          size: 'tiny',
          quaternary: true,
          type: 'error',
          disabled: Boolean(syncStore.activeTasks[row.id]),
          onClick: () => handleDeleteHistory(row)
        }, { default: () => '删除' })
      ])
    }
  }
]
</script>

<style scoped>
.sync-table :deep(.n-data-table-th) {
  height: 38px;
  padding: 6px 12px;
  font-size: 13px !important;
  font-weight: 600;
  transition: color 160ms var(--ease-out);
}

.sync-table :deep(.n-data-table-td) {
  height: 40px;
  padding: 6px 12px;
  font-size: 13px !important;
  transition: background-color 160ms var(--ease-out);
}

@media (hover: hover) and (pointer: fine) {
  .sync-table :deep(.n-data-table-tr:hover .n-data-table-td) {
    background-color: #f8fafc !important;
  }
  :global(.dark) .sync-table :deep(.n-data-table-tr:hover .n-data-table-td) {
    background-color: #1f2937 !important;
  }
}

.sync-table :deep(.n-tag) {
  height: 22px;
  padding: 0 6px;
  font-size: 12px !important;
  transition: background-color 180ms ease, color 180ms ease;
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
