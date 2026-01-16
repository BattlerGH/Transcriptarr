import axios from 'axios'
import type {
  SystemStatus,
  Worker,
  WorkerPoolStats,
  AddWorkerRequest,
  Job,
  JobList,
  QueueStats,
  CreateJobRequest,
  ScanRule,
  CreateScanRuleRequest,
  ScannerStatus,
  ScanRequest,
  ScanResult
} from '@/types/api'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// System API
export const systemApi = {
  getStatus: () => api.get<SystemStatus>('/status'),
  getHealth: () => api.get('/health')
}

// Workers API
export const workersApi = {
  getAll: () => api.get<Worker[]>('/workers'),
  getStats: () => api.get<WorkerPoolStats>('/workers/stats'),
  getById: (id: string) => api.get<Worker>(`/workers/${id}`),
  add: (data: AddWorkerRequest) => api.post<Worker>('/workers', data),
  remove: (id: string, timeout = 30) => api.delete(`/workers/${id}`, { params: { timeout } }),
  startPool: (cpuWorkers = 0, gpuWorkers = 0) =>
    api.post('/workers/pool/start', null, { params: { cpu_workers: cpuWorkers, gpu_workers: gpuWorkers } }),
  stopPool: (timeout = 30) => api.post('/workers/pool/stop', null, { params: { timeout } })
}

// Jobs API
export const jobsApi = {
  getAll: (statusFilter?: string, page = 1, pageSize = 50) =>
    api.get<JobList>('/jobs', { params: { status_filter: statusFilter, page, page_size: pageSize } }),
  getStats: () => api.get<QueueStats>('/jobs/stats'),
  getById: (id: string) => api.get<Job>(`/jobs/${id}`),
  create: (data: CreateJobRequest) => api.post<Job>('/jobs', data),
  retry: (id: string) => api.post<Job>(`/jobs/${id}/retry`),
  cancel: (id: string) => api.delete(`/jobs/${id}`),
  clearCompleted: () => api.post('/jobs/queue/clear')
}

// Scan Rules API
export const scanRulesApi = {
  getAll: (enabledOnly = false) => api.get<ScanRule[]>('/scan-rules', { params: { enabled_only: enabledOnly } }),
  getById: (id: number) => api.get<ScanRule>(`/scan-rules/${id}`),
  create: (data: CreateScanRuleRequest) => api.post<ScanRule>('/scan-rules', data),
  update: (id: number, data: Partial<CreateScanRuleRequest>) => api.put<ScanRule>(`/scan-rules/${id}`, data),
  delete: (id: number) => api.delete(`/scan-rules/${id}`),
  toggle: (id: number) => api.post<ScanRule>(`/scan-rules/${id}/toggle`)
}

// Scanner API
export const scannerApi = {
  getStatus: () => api.get<ScannerStatus>('/scanner/status'),
  scan: (data: ScanRequest) => api.post<ScanResult>('/scanner/scan', data),
  startScheduler: (cronExpression: string, paths: string[], recursive = true) =>
    api.post('/scanner/scheduler/start', { enabled: true, cron_expression: cronExpression, paths, recursive }),
  stopScheduler: () => api.post('/scanner/scheduler/stop'),
  startWatcher: (paths: string[], recursive = true) =>
    api.post('/scanner/watcher/start', { enabled: true, paths, recursive }),
  stopWatcher: () => api.post('/scanner/watcher/stop'),
  analyzeFile: (filePath: string) => api.post('/scanner/analyze', null, { params: { file_path: filePath } })
}

export default api

