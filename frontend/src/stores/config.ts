import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useConfigStore = defineStore('config', () => {
  const operationMode = ref<'standalone' | 'bazarr_slave'>('standalone')
  const hasGPU = ref(false)
  const loading = ref(false)

  const isStandalone = computed(() => operationMode.value === 'standalone')
  const isBazarrSlave = computed(() => operationMode.value === 'bazarr_slave')

  async function fetchConfig() {
    loading.value = true
    try {
      // Get operation mode from settings
      const response = await axios.get('/api/settings/operation_mode')
      operationMode.value = response.data.value === 'bazarr_slave' ? 'bazarr_slave' : 'standalone'
    } catch (error) {
      console.error('Failed to fetch operation mode:', error)
    } finally {
      loading.value = false
    }
  }

  async function detectGPU() {
    try {
      // Try to get system resources to detect GPU
      const response = await axios.get('/api/system/resources')
      hasGPU.value = response.data.gpus && response.data.gpus.length > 0
    } catch (error) {
      // If endpoint doesn't exist, assume no GPU detection available
      hasGPU.value = false
    }
  }

  return {
    operationMode,
    hasGPU,
    loading,
    isStandalone,
    isBazarrSlave,
    fetchConfig,
    detectGPU
  }
})

