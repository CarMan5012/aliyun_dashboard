<template>
  <div ref="chartRef" class="w-full h-full min-h-[260px]"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { useThemeStore } from '@/store'

const props = defineProps<{
  data: { name: string; value: number }[]
  title?: string
}>()

const chartRef = ref<HTMLDivElement | null>(null)
const themeStore = useThemeStore()
let chartInstance: echarts.ECharts | null = null

function initChart() {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value)
  updateChart()
}

function updateChart() {
  if (!chartInstance) return

  const isDark = themeStore.theme === 'dark'
  const textColor = isDark ? '#cbd5e1' : '#1e293b'
  const legendColor = isDark ? '#94a3b8' : '#64748b'
  const borderColor = isDark ? '#111827' : '#ffffff'
  const tooltipBg = isDark ? '#1f2937' : '#ffffff'
  const tooltipBorder = isDark ? '#374151' : '#e2e8f0'
  const tooltipText = isDark ? '#cbd5e1' : '#1e293b'

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      textStyle: {
        color: tooltipText,
      },
    },
    legend: {
      bottom: '0%',
      left: 'center',
      textStyle: {
        color: legendColor,
      },
    },
    series: [
      {
        name: props.title || '资源占比',
        type: 'pie',
        radius: ['45%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: borderColor,
          borderWidth: 2,
        },
        label: {
          show: false,
          position: 'center',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 16,
            fontWeight: 'bold',
            color: textColor,
          },
        },
        labelLine: {
          show: false,
        },
        data: props.data,
        color: ['#1677ff', '#52c41a', '#faad14', '#ff4d4f', '#722ed1'],
      },
    ],
  }

  chartInstance.setOption(option)
}

const resizeHandler = () => {
  chartInstance?.resize()
}

watch(() => props.data, () => {
  updateChart()
}, { deep: true })

watch(() => themeStore.theme, () => {
  updateChart()
})

onMounted(() => {
  initChart()
  window.addEventListener('resize', resizeHandler)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeHandler)
  chartInstance?.dispose()
})
</script>
