<template>
  <div class="bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-5 shadow-sm hover:shadow-card-hover hover:border-primary/20 dark:hover:border-primary/20 hover:-translate-y-1 transition-all duration-300 flex items-center justify-between">
    <div class="space-y-1.5">
      <span class="text-xs text-slate-550 dark:text-slate-400 font-semibold tracking-wide uppercase">{{ title }}</span>
      <h3 class="text-3xl font-bold text-slate-850 dark:text-slate-100 tracking-tight">{{ value }}</h3>
    </div>
    <div class="w-12 h-12 rounded-xl bg-slate-50 dark:bg-slate-900 flex items-center justify-center border border-borderLight dark:border-borderDark" :class="[iconColor]">
      <Icon :icon="icon" :width="22" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'

defineProps<{
  title: string
  value: number
  icon: string
  iconColor: string
}>()
</script>
