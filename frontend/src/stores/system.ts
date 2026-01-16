import { defineStore } from 'pinia'
import { ref } from 'vue'
import { systemApi } from '@/services/api'
import type { SystemStatus } from '@/types/api'

export const useSystemStore = defineStore('system', () => {
  const status = ref<SystemStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const isOnline = ref(true)

  async function fetchStatus() {
    loading.value = true
    error.value = null
    try {
      const response = await systemApi.getStatus()
      status.value = response.data
      isOnline.value = true
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch system status'
      isOnline.value = false
      throw err
    } finally {
      loading.value = false
    }
  }

  async function checkHealth() {
    try {
      await systemApi.getHealth()
      isOnline.value = true
      return true
    } catch (err) {
      isOnline.value = false
      return false
    }
  }

  return {
    status,
    loading,
    error,
    isOnline,
    fetchStatus,
    checkHealth
  }
})

