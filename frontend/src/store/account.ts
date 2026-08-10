import { defineStore } from 'pinia'
import { ref } from 'vue'
import { fetchAccountsFull, createAccount, updateAccountApi, deleteAccount } from '@/api'
import type { CloudAccountItem, AccountSaveResponse } from '@/api'

export const useAccountStore = defineStore('account', () => {
  const accounts = ref<CloudAccountItem[]>([])
  const activeAccount = ref<string>('全部账号')
  const activeAccountId = ref<number | null>(null)
  const loading = ref(false)

  async function loadAccounts() {
    if (loading.value) return
    loading.value = true
    try {
      accounts.value = await fetchAccountsFull()
    } catch (e) {
      console.error('Failed to load accounts:', e)
    } finally {
      loading.value = false
    }
  }

  async function addAccount(alias: string, ak: string, sk: string, interval: number): Promise<AccountSaveResponse> {
    const res = await createAccount(alias, ak, sk, interval)
    if (res && res.data) {
      accounts.value.push(res.data)
    }
    return res
  }

  async function removeAccount(id: number) {
    await deleteAccount(id)
    accounts.value = accounts.value.filter((a) => a.id !== id)
    if (activeAccountId.value === id) {
      activeAccountId.value = null
      activeAccount.value = '全部账号'
    }
  }

  async function updateAccount(id: number, payload: any): Promise<AccountSaveResponse> {
    const res = await updateAccountApi(id, payload)
    if (res && res.data) {
      accounts.value = accounts.value.map((a) => (a.id === id ? res.data : a))
      if (activeAccountId.value === id) {
        activeAccount.value = res.data.account_alias
      }
    }
    return res
  }

  return {
    accounts,
    activeAccount,
    activeAccountId,
    loading,
    loadAccounts,
    addAccount,
    removeAccount,
    updateAccount,
  }
})
