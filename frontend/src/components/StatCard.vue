<template>
  <div class="stat-card bg-white dark:bg-cardDark border border-borderLight dark:border-borderDark rounded-xl p-4 sm:p-5 shadow-sm hover:shadow-card-hover hover:border-primary/30 dark:hover:border-primary/30 flex items-center justify-between cursor-pointer select-none">
    <div class="space-y-1">
      <span class="text-[13px] text-slate-500 dark:text-slate-400 font-medium tracking-wide">{{ title }}</span>
      <h3 class="text-2xl font-semibold text-slate-800 dark:text-slate-100 tracking-tight stat-number">{{ value }}</h3>
    </div>
    <div class="w-11 h-11 rounded-xl bg-slate-50 dark:bg-slate-900 flex items-center justify-center border border-borderLight dark:border-borderDark stat-icon-wrap" :class="[iconColor]">
      <Icon :icon="icon" :width="20" class="stat-icon" />
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

<style scoped>
.stat-card {
  transition: transform 180ms cubic-bezier(0.23, 1, 0.32, 1), box-shadow 180ms ease, border-color 180ms ease;
}

@media (hover: hover) and (pointer: fine) {
  .stat-card:hover {
    transform: translateY(-2px);
  }
  .stat-card:hover .stat-icon-wrap {
    transform: scale(1.05);
  }
}

.stat-card:active {
  transform: scale(0.98) translateY(0);
}

.stat-icon-wrap {
  transition: transform 200ms cubic-bezier(0.34, 1.56, 0.64, 1);
}

.stat-number {
  font-variant-numeric: tabular-nums;
}
</style>
