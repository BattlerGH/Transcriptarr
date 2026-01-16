import { defineStore } from 'pinia'
import { ref } from 'vue'
import { workersApi } from '@/services/api'
import type { Worker, WorkerPoolStats, AddWorkerRequest } from '@/types/api'

export const useWorkersStore = defineStore('workers', () => {
  const workers = ref<Worker[]>([])
  const stats = ref<WorkerPoolStats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchWorkers() {
    loading.value = true
    error.value = null
    try {
      const response = await workersApi.getAll()
      workers.value = response.data
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch workers'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      const response = await workersApi.getStats()
      stats.value = response.data
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch worker stats'
      throw err
    }
  }

  async function addWorker(data: AddWorkerRequest) {
    loading.value = true
    error.value = null
    try {
      const response = await workersApi.add(data)
      workers.value.push(response.data)
      await fetchStats()
      return response.data
    } catch (err: any) {
      error.value = err.message || 'Failed to add worker'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function removeWorker(id: string) {
    loading.value = true
    error.value = null
    try {
      await workersApi.remove(id)
      workers.value = workers.value.filter(w => w.worker_id !== id)
      await fetchStats()
    } catch (err: any) {
      error.value = err.message || 'Failed to remove worker'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function startPool(cpuWorkers: number, gpuWorkers: number) {
    loading.value = true
    error.value = null
    try {
      await workersApi.startPool(cpuWorkers, gpuWorkers)
      await fetchWorkers()
      await fetchStats()
    } catch (err: any) {
      error.value = err.message || 'Failed to start pool'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function stopPool() {
    loading.value = true
    error.value = null
    try {
      await workersApi.stopPool()
      workers.value = []
      await fetchStats()
    } catch (err: any) {
      error.value = err.message || 'Failed to stop pool'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    workers,
    stats,
    loading,
    error,
    fetchWorkers,
    fetchStats,
    addWorker,
    removeWorker,
    startPool,
    stopPool
  }
})

