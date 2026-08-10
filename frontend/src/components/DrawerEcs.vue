<template>
  <div v-if="record" class="space-y-6 text-slate-600 dark:text-slate-300">
    <!-- 头部概要 -->
    <div class="flex items-center gap-3 pb-4 border-b border-borderLight dark:border-borderDark">
      <div class="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
        <Icon icon="lucide:server" :width="20" />
      </div>
      <div>
        <h4 class="font-bold text-slate-800 dark:text-slate-200 text-sm">{{ record.details.instance_name || '未命名实例' }}</h4>
        <span class="text-[10px] text-slate-450 dark:text-slate-500 font-mono">{{ record.details.instance_id }}</span>
      </div>
    </div>

    <!-- 基础信息 -->
    <div class="space-y-3">
      <h5 class="text-xs font-bold text-slate-400 dark:text-slate-500 flex items-center gap-1.5 uppercase tracking-wider">
        <Icon icon="lucide:info" :width="13" />
        基础属性
      </h5>
      <div class="grid grid-cols-2 gap-4 bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-borderLight dark:border-borderDark text-xs">
        <div>
          <span class="text-slate-400 dark:text-slate-500 block mb-1">实例状态</span>
          <span class="px-2 py-0.5 rounded border border-success/20 bg-success/10 text-success font-semibold inline-block" v-if="record.details.status === 'Running'">
            运行中
          </span>
          <span class="px-2 py-0.5 rounded border border-borderLight dark:border-borderDark bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 font-semibold inline-block" v-else>
            {{ record.details.status }}
          </span>
        </div>
        <div>
          <span class="text-slate-400 dark:text-slate-500 block mb-1">区域</span>
          <span class="font-bold text-slate-700 dark:text-slate-200">{{ record.details.region_id }}</span>
        </div>
        <div>
          <span class="text-slate-400 dark:text-slate-500 block mb-1">账号归属</span>
          <span class="font-bold text-primary">{{ record.account_name }}</span>
        </div>
        <div>
          <span class="text-slate-400 dark:text-slate-500 block mb-1">付费方式</span>
          <span class="font-bold text-slate-700 dark:text-slate-200">{{ record.details.charge_type }}</span>
        </div>
      </div>
    </div>

    <!-- 规格配置 -->
    <div class="space-y-3">
      <h5 class="text-xs font-bold text-slate-400 dark:text-slate-500 flex items-center gap-1.5 uppercase tracking-wider">
        <Icon icon="lucide:cpu" :width="13" />
        硬件规格
      </h5>
      <div class="grid grid-cols-2 gap-4 bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-borderLight dark:border-borderDark text-xs">
        <div>
          <span class="text-slate-400 dark:text-slate-500 block mb-1">处理器 (CPU)</span>
          <span class="font-bold text-slate-800 dark:text-slate-200">{{ record.details.cpu }} 核</span>
        </div>
        <div>
          <span class="text-slate-400 dark:text-slate-500 block mb-1">内存容量</span>
          <span class="font-bold text-slate-800 dark:text-slate-200">{{ formatMemory(record.details.memory) }}</span>
        </div>
      </div>
    </div>

    <!-- 网络信息 -->
    <div class="space-y-3">
      <h5 class="text-xs font-bold text-slate-400 dark:text-slate-500 flex items-center gap-1.5 uppercase tracking-wider">
        <Icon icon="lucide:globe" :width="13" />
        网络与IP
      </h5>
      <div class="space-y-2 bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-borderLight dark:border-borderDark text-xs">
        <div class="flex justify-between items-center py-1">
          <span class="text-slate-400 dark:text-slate-500">公网 IP</span>
          <span class="font-mono font-semibold text-slate-800 dark:text-slate-200">{{ record.details.public_ips?.join(', ') || '无' }}</span>
        </div>
        <div class="flex justify-between items-center py-1 border-t border-borderLight dark:border-borderDark">
          <span class="text-slate-400 dark:text-slate-500">弹性公网 IP (EIP)</span>
          <span class="font-mono font-semibold text-slate-800 dark:text-slate-200">{{ record.details.eip || '无' }}</span>
        </div>
        <div class="flex justify-between items-center py-1 border-t border-borderLight dark:border-borderDark">
          <span class="text-slate-400 dark:text-slate-500">内网 IP</span>
          <span class="font-mono font-semibold text-slate-800 dark:text-slate-200">{{ record.details.private_ips?.join(', ') || '无' }}</span>
        </div>
      </div>
    </div>

    <!-- 时间节点 -->
    <div class="space-y-3">
      <h5 class="text-xs font-bold text-slate-400 dark:text-slate-500 flex items-center gap-1.5 uppercase tracking-wider">
        <Icon icon="lucide:calendar" :width="13" />
        生命周期
      </h5>
      <div class="grid grid-cols-2 gap-4 bg-slate-50 dark:bg-slate-900/50 p-4 rounded-xl border border-borderLight dark:border-borderDark text-xs">
        <div>
          <span class="text-slate-400 dark:text-slate-500 block mb-1">创建时间</span>
          <span class="font-medium font-mono text-slate-700 dark:text-slate-300">{{ formatDate(record.details.creation_time) }}</span>
        </div>
        <div>
          <span class="text-slate-400 dark:text-slate-500 block mb-1">释放时间</span>
          <span class="font-medium font-mono text-amber-600 dark:text-yellow-500">{{ formatDate(record.details.expired_time) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { ResourceItem } from '@/api'

defineProps<{
  record: ResourceItem | null
}>()

function formatMemory(memMB?: number): string {
  if (!memMB) return '-'
  if (memMB < 1024) return `${memMB} MB`
  const gb = memMB / 1024
  return `${gb % 1 === 0 ? gb.toFixed(0) : gb.toFixed(1)} GB`
}

function formatDate(dateStr?: string): string {
  if (!dateStr) return '-'
  return dateStr.replace('T', ' ').replace('Z', '')
}
</script>
