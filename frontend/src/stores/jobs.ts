import { defineStore } from 'pinia'
import { ref } from 'vue'
import { jobsApi } from '@/services/api'
import type { Job, JobList, QueueStats, CreateJobRequest } from '@/types/api'

export const useJobsStore = defineStore('jobs', () => {
  const jobs = ref<Job[]>([])
  const stats = ref<QueueStats | null>(null)
  const totalJobs = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(50)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchJobs(statusFilter?: string, page = 1) {
    loading.value = true
    error.value = null
    currentPage.value = page
    try {
      const response = await jobsApi.getAll(statusFilter, page, pageSize.value)
      jobs.value = response.data.jobs
      totalJobs.value = response.data.total
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch jobs'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      const response = await jobsApi.getStats()
      stats.value = response.data
    } catch (err: any) {
      error.value = err.message || 'Failed to fetch job stats'
      throw err
    }
  }

  async function createJob(data: CreateJobRequest) {
    loading.value = true
    error.value = null
    try {
      const response = await jobsApi.create(data)
      jobs.value.unshift(response.data)
      await fetchStats()
      return response.data
    } catch (err: any) {
      error.value = err.message || 'Failed to create job'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function retryJob(id: string) {
    loading.value = true
    error.value = null
    try {
      const response = await jobsApi.retry(id)
      const index = jobs.value.findIndex(j => j.id === id)
      if (index !== -1) {
        jobs.value[index] = response.data
      }
      await fetchStats()
      return response.data
    } catch (err: any) {
      error.value = err.message || 'Failed to retry job'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelJob(id: string) {
    loading.value = true
    error.value = null
    try {
      await jobsApi.cancel(id)
      const index = jobs.value.findIndex(j => j.id === id)
      if (index !== -1) {
        jobs.value[index].status = 'cancelled'
      }
      await fetchStats()
    } catch (err: any) {
      error.value = err.message || 'Failed to cancel job'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function clearCompleted() {
    loading.value = true
    error.value = null
    try {
      await jobsApi.clearCompleted()
      jobs.value = jobs.value.filter(j => j.status !== 'completed')
      await fetchStats()
    } catch (err: any) {
      error.value = err.message || 'Failed to clear completed jobs'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    jobs,
    stats,
    totalJobs,
    currentPage,
    pageSize,
    loading,
    error,
    fetchJobs,
    fetchStats,
    createJob,
    retryJob,
    cancelJob,
    clearCompleted
  }
})

