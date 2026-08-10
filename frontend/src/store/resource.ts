import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchResources, searchResources, fetchDbStatus } from '@/api'
import type { ResourceItem } from '@/api'
import { useAccountStore } from './account'
import router from '@/router'

export const useResourceStore = defineStore('resource', () => {
  const accountStore = useAccountStore()

  const ecsList = ref<ResourceItem[]>([])
  const eipList = ref<ResourceItem[]>([])
  const domainList = ref<ResourceItem[]>([])
  const sslList = ref<ResourceItem[]>([])

  const loading = ref(false)
  const isDbEmpty = ref(false)

  const searchKeyword = ref('')
  const searchResults = ref<ResourceItem[]>([])
  const isSearchMode = ref(false)

  // 侧边栏折叠状态
  const sidebarCollapsed = ref(false)

  // 资源多选与抽屉详情状态
  const selectedRowKeys = ref<number[]>([])
  const activeDetailRow = ref<ResourceItem | null>(null)
  const isDetailDrawerOpen = ref(false)

  // 自定义列显隐状态（保存列的 key 数组，供表格使用）
  const visibleColumns = ref<Record<string, string[]>>({
    ECS: ['account_name', 'instance_name', 'instance_id', 'region_id', 'status', 'cpu', 'memory', 'public_ips', 'private_ips', 'eip', 'expired_time', 'action'],
    EIP: ['account_name', 'ip_address', 'bandwidth', 'charge_type', 'instance_id', 'status', 'creation_time'],
    Domain: ['account_name', 'domain_name', 'registration_date', 'expiration_date', 'remaining_days'],
    SSL: ['account_name', 'cert_name', 'domain', 'cert_type', 'brand', 'cert_start_time', 'cert_end_time', 'remaining_days', 'status']
  })

  const typeErrors = ref<Record<string, string | null>>({
    ECS: null,
    EIP: null,
    Domain: null,
    SSL: null
  })

  const dbHealthState = ref<'empty' | 'available' | 'unavailable'>('available')

  async function checkDbEmpty() {
    try {
      const isEmpty = await fetchDbStatus()
      isDbEmpty.value = isEmpty
      dbHealthState.value = isEmpty ? 'empty' : 'available'
    } catch (e) {
      isDbEmpty.value = false
      dbHealthState.value = 'unavailable'
      console.error('Failed to check DB status:', e)
    }
  }

  async function loadResourcesByType(type: 'ECS' | 'EIP' | 'Domain' | 'SSL') {
    try {
      const data = await fetchResources(type, accountStore.activeAccount, accountStore.activeAccountId)
      if (type === 'ECS') ecsList.value = data
      else if (type === 'EIP') eipList.value = data
      else if (type === 'Domain') domainList.value = data
      else if (type === 'SSL') sslList.value = data
      typeErrors.value[type] = null
    } catch (e: any) {
      const msg = e.response?.data?.detail || e.message || '数据加载失败'
      typeErrors.value[type] = msg
      console.error(`Failed to load ${type}:`, e)
      throw e
    }
  }

  async function loadAllResources() {
    if (loading.value) return
    const hasCachedData = ecsList.value.length > 0 || eipList.value.length > 0 || domainList.value.length > 0 || sslList.value.length > 0
    if (!hasCachedData) {
      loading.value = true
    }
    isSearchMode.value = false
    searchKeyword.value = ''
    try {
      await Promise.allSettled([
        loadResourcesByType('ECS'),
        loadResourcesByType('EIP'),
        loadResourcesByType('Domain'),
        loadResourcesByType('SSL'),
        checkDbEmpty()
      ])
    } finally {
      loading.value = false
    }
  }

  async function performGlobalSearch() {
    if (!searchKeyword.value.trim()) {
      isSearchMode.value = false
      return
    }
    loading.value = true
    isSearchMode.value = true
    try {
      searchResults.value = await searchResources(searchKeyword.value, accountStore.activeAccountId)
      
      // 搜索成功后，自动跳转至首个有搜索结果的 Tab
      if (searchResults.value.length > 0) {
        const firstTabWithResults = ['ECS', 'EIP', 'Domain', 'SSL'].find(t => 
          searchResults.value.some(r => r.resource_type === t)
        )
        if (firstTabWithResults) {
          const currentRoute = router.currentRoute.value
          if (currentRoute.path !== '/resources' || currentRoute.query.tab !== firstTabWithResults) {
            await router.push({
              path: '/resources',
              query: { tab: firstTabWithResults }
            })
          }
        }
      } else {
        // 如果无结果，仍跳转至资产中心以展示空白状态
        const currentRoute = router.currentRoute.value
        if (currentRoute.path !== '/resources') {
          await router.push('/resources')
        }
      }
    } catch (e) {
      console.error('Global search failed:', e)
      searchResults.value = []
    } finally {
      loading.value = false
    }
  }

  function clearSearch() {
    searchKeyword.value = ''
    isSearchMode.value = false
    searchResults.value = []
  }

  // 辅助计算
  const currentEcs = computed(() => {
    if (isSearchMode.value) {
      return searchResults.value.filter(r => r.resource_type === 'ECS')
    }
    return ecsList.value
  })
  const currentEip = computed(() => {
    if (isSearchMode.value) {
      return searchResults.value.filter(r => r.resource_type === 'EIP')
    }
    return eipList.value
  })
  const currentDomain = computed(() => {
    if (isSearchMode.value) {
      return searchResults.value.filter(r => r.resource_type === 'Domain')
    }
    return domainList.value
  })
  const currentSsl = computed(() => {
    if (isSearchMode.value) {
      return searchResults.value.filter(r => r.resource_type === 'SSL')
    }
    return sslList.value
  })

  return {
    ecsList,
    eipList,
    domainList,
    sslList,
    typeErrors,
    loading,
    isDbEmpty,
    dbHealthState,
    searchKeyword,
    searchResults,
    isSearchMode,
    sidebarCollapsed,
    selectedRowKeys,
    activeDetailRow,
    isDetailDrawerOpen,
    visibleColumns,
    loadAllResources,
    loadResourcesByType,
    performGlobalSearch,
    clearSearch,
    checkDbEmpty,
    currentEcs,
    currentEip,
    currentDomain,
    currentSsl,
  }
})
