import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type Account, type Stats } from '@/api'

export const useAccountsStore = defineStore('accounts', () => {
  const accounts = ref<Account[]>([])
  const total = ref(0)
  const loading = ref(false)
  const stats = ref<Stats | null>(null)

  async function fetchAccounts(params: {
    page?: number
    per_page?: number
    status?: string
    search?: string
  }) {
    loading.value = true
    try {
      const data = await api.getAccounts(params)
      accounts.value = data.items
      total.value = data.total
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    stats.value = await api.getStats()
  }

  return { accounts, total, loading, stats, fetchAccounts, fetchStats }
})
