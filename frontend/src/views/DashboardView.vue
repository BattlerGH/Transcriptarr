<template>
  <div class="dashboard">
    <div class="page-header">
      <h1 class="page-title">Dashboard</h1>
      <div class="header-actions">
        <span class="refresh-indicator" v-if="!loading">
          Auto-refresh: <span class="text-success">{{ countdown }}s</span>
        </span>
        <button @click="loadData" class="btn btn-secondary" :disabled="loading">
          <span v-if="loading">Loading...</span>
          <span v-else>↻ Refresh Now</span>
        </button>
      </div>
    </div>

    <div v-if="loading && !systemStatus" class="spinner"></div>

    <div v-else-if="systemStatus" class="dashboard-content">
      <!-- Top Row: System Overview Cards -->
      <div class="dashboard-grid">
        <!-- System Overview -->
        <div class="card highlight-card">
          <div class="card-header">
            <div class="header-icon">🖥️</div>
            <h2 class="card-title">System Status</h2>
            <span :class="['badge', systemStatus.system.status === 'running' ? 'badge-completed' : 'badge-failed']">
              {{ systemStatus.system.status }}
            </span>
          </div>
          <div class="card-body">
            <div class="stat-row">
              <span class="stat-label">Uptime:</span>
              <span class="stat-value">{{ formatUptime(systemStatus.system.uptime_seconds) }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Version:</span>
              <span class="stat-value">v1.0.0</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Mode:</span>
              <span class="stat-value badge badge-info">
                {{ systemStatus.system.mode || 'Standalone' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Workers Overview -->
        <div class="card">
          <div class="card-header">
            <div class="header-icon">⚙️</div>
            <h2 class="card-title">Workers</h2>
            <router-link to="/workers" class="btn btn-secondary btn-sm">Manage</router-link>
          </div>
          <div class="card-body">
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-number">{{ systemStatus.workers?.pool?.total_workers || 0 }}</div>
                <div class="stat-label">Total</div>
              </div>
              <div class="stat-item">
                <div class="stat-number text-success">{{ systemStatus.workers?.pool?.idle_workers || 0 }}</div>
                <div class="stat-label">Idle</div>
              </div>
              <div class="stat-item">
                <div class="stat-number text-primary">{{ systemStatus.workers?.pool?.busy_workers || 0 }}</div>
                <div class="stat-label">Busy</div>
              </div>
              <div class="stat-item">
                <div class="stat-number">{{ systemStatus.workers?.jobs?.completed || 0 }}</div>
                <div class="stat-label">Completed</div>
              </div>
            </div>
            <div class="progress-section">
              <div class="progress-label">
                <span>Worker Utilization</span>
                <span>{{ workerUtilization }}%</span>
              </div>
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: workerUtilization + '%', backgroundColor: getUsageColor(workerUtilization) }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Queue Overview -->
        <div class="card">
          <div class="card-header">
            <div class="header-icon">📋</div>
            <h2 class="card-title">Job Queue</h2>
            <router-link to="/queue" class="btn btn-secondary btn-sm">View All</router-link>
          </div>
          <div class="card-body">
            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-number">{{ systemStatus.queue?.total || 0 }}</div>
                <div class="stat-label">Total</div>
              </div>
              <div class="stat-item">
                <div class="stat-number text-warning">{{ systemStatus.queue?.queued || 0 }}</div>
                <div class="stat-label">Queued</div>
              </div>
              <div class="stat-item">
                <div class="stat-number text-primary">{{ systemStatus.queue?.processing || 0 }}</div>
                <div class="stat-label">Processing</div>
              </div>
              <div class="stat-item">
                <div class="stat-number text-success">{{ systemStatus.queue?.completed || 0 }}</div>
                <div class="stat-label">Completed</div>
              </div>
            </div>
            <div class="queue-chart">
              <div
                class="queue-bar queue-completed"
                :style="{ width: queuePercentage('completed') + '%' }"
                :title="`Completed: ${systemStatus.queue.completed}`"
              ></div>
              <div
                class="queue-bar queue-processing"
                :style="{ width: queuePercentage('processing') + '%' }"
                :title="`Processing: ${systemStatus.queue.processing}`"
              ></div>
              <div
                class="queue-bar queue-queued"
                :style="{ width: queuePercentage('queued') + '%' }"
                :title="`Queued: ${systemStatus.queue.queued}`"
              ></div>
              <div
                class="queue-bar queue-failed"
                :style="{ width: queuePercentage('failed') + '%' }"
                :title="`Failed: ${systemStatus.queue.failed}`"
              ></div>
            </div>
          </div>
        </div>

        <!-- Scanner Overview -->
        <div class="card">
          <div class="card-header">
            <div class="header-icon">📁</div>
            <h2 class="card-title">Library Scanner</h2>
            <router-link to="/scanner" class="btn btn-secondary btn-sm">Configure</router-link>
          </div>
          <div class="card-body">
            <div class="stat-row">
              <span class="stat-label">Scheduler:</span>
              <span :class="['badge', systemStatus.scanner.scheduler_running ? 'badge-completed' : 'badge-cancelled']">
                {{ systemStatus.scanner.scheduler_running ? 'Running' : 'Stopped' }}
              </span>
            </div>
            <div class="stat-row">
              <span class="stat-label">File Watcher:</span>
              <span :class="['badge', systemStatus.scanner.watcher_running ? 'badge-completed' : 'badge-cancelled']">
                {{ systemStatus.scanner.watcher_running ? 'Active' : 'Inactive' }}
              </span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Last Scan:</span>
              <span class="stat-value">{{ formatDate(systemStatus.scanner.last_scan_time) }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-label">Total Scans:</span>
              <span class="stat-value">{{ systemStatus.scanner.total_scans || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- System Resources Section -->
      <div class="resources-section">
        <h2 class="section-title">
          <span class="section-icon">💻</span>
          System Resources
        </h2>
        <div class="resources-grid">
          <!-- CPU Card -->
          <div class="card resource-card">
            <div class="card-header">
              <h3 class="card-title">CPU Usage</h3>
              <span class="resource-value">{{ systemResources.cpu?.usage_percent?.toFixed(1) || 0 }}%</span>
            </div>
            <div class="card-body">
              <div class="progress-bar large">
                <div
                  class="progress-fill"
                  :style="{
                    width: (systemResources.cpu?.usage_percent || 0) + '%',
                    backgroundColor: getUsageColor(systemResources.cpu?.usage_percent || 0)
                  }"
                ></div>
              </div>
              <div class="resource-details">
                <div class="detail-item">
                  <span class="detail-label">Cores:</span>
                  <span class="detail-value">{{ systemResources.cpu?.count_logical || 0 }} ({{ systemResources.cpu?.count_physical || 0 }} physical)</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Frequency:</span>
                  <span class="detail-value">{{ (systemResources.cpu?.frequency_mhz || 0).toFixed(0) }} MHz</span>
                </div>
              </div>
            </div>
          </div>

          <!-- RAM Card -->
          <div class="card resource-card">
            <div class="card-header">
              <h3 class="card-title">RAM Usage</h3>
              <span class="resource-value">{{ systemResources.memory?.usage_percent?.toFixed(1) || 0 }}%</span>
            </div>
            <div class="card-body">
              <div class="progress-bar large">
                <div
                  class="progress-fill"
                  :style="{
                    width: (systemResources.memory?.usage_percent || 0) + '%',
                    backgroundColor: getUsageColor(systemResources.memory?.usage_percent || 0)
                  }"
                ></div>
              </div>
              <div class="resource-details">
                <div class="detail-item">
                  <span class="detail-label">Used:</span>
                  <span class="detail-value">{{ (systemResources.memory?.used_gb || 0).toFixed(2) }} GB</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Total:</span>
                  <span class="detail-value">{{ (systemResources.memory?.total_gb || 0).toFixed(2) }} GB</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Free:</span>
                  <span class="detail-value">{{ (systemResources.memory?.free_gb || 0).toFixed(2) }} GB</span>
                </div>
              </div>
            </div>
          </div>

          <!-- GPU Cards -->
          <div
            v-for="(gpu, index) in systemResources.gpus"
            :key="index"
            class="card resource-card"
          >
            <div class="card-header">
              <h3 class="card-title">{{ gpu.name || `GPU ${index}` }}</h3>
              <span class="resource-value">{{ gpu.utilization_percent?.toFixed(1) || 0 }}%</span>
            </div>
            <div class="card-body">
              <div class="progress-bar large">
                <div
                  class="progress-fill"
                  :style="{
                    width: (gpu.utilization_percent || 0) + '%',
                    backgroundColor: getUsageColor(gpu.utilization_percent || 0)
                  }"
                ></div>
              </div>
              <div class="resource-details">
                <div class="detail-item">
                  <span class="detail-label">VRAM Used:</span>
                  <span class="detail-value">
                    {{ (gpu.memory_used_mb / 1024).toFixed(2) }} GB
                  </span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">VRAM Total:</span>
                  <span class="detail-value">
                    {{ (gpu.memory_total_mb / 1024).toFixed(2) }} GB
                  </span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">VRAM Usage:</span>
                  <span class="detail-value">
                    {{ ((gpu.memory_used_mb / gpu.memory_total_mb) * 100).toFixed(1) }}%
                  </span>
                </div>
              </div>
            </div>
          </div>

          <!-- No GPUs Message -->
          <div v-if="!systemResources.gpus || systemResources.gpus.length === 0" class="card resource-card empty-gpu">
            <div class="card-body">
              <div class="empty-state">
                <p>No GPUs detected</p>
                <small>CPU-only mode active</small>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Recent Jobs Section -->
      <div class="recent-jobs-section">
        <div class="section-header">
          <h2 class="section-title">
            <span class="section-icon">⏱️</span>
            Recent Jobs
          </h2>
          <router-link to="/queue" class="btn btn-secondary">View All Jobs →</router-link>
        </div>

        <div v-if="recentJobs.length === 0" class="empty-state">
          <p>No jobs yet</p>
        </div>

        <div v-else class="table-container">
          <table class="jobs-table">
            <thead>
              <tr>
                <th>File Name</th>
                <th>Status</th>
                <th>Languages</th>
                <th>Progress</th>
                <th>Worker</th>
                <th>Created</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="job in recentJobs" :key="job.id" :class="'row-' + job.status">
                <td class="file-name">
                  <span class="file-icon">📄</span>
                  {{ job.file_name }}
                </td>
                <td>
                  <span :class="['badge', `badge-${job.status}`]">
                    {{ job.status }}
                  </span>
                </td>
                <td class="languages">
                  <span class="lang-badge">{{ job.source_lang }}</span>
                  <span class="arrow">→</span>
                  <span class="lang-badge">{{ job.target_lang }}</span>
                </td>
                <td>
                  <div class="progress-cell">
                    <div class="progress-bar small">
                      <div
                        class="progress-fill"
                        :style="{ width: job.progress + '%' }"
                      ></div>
                    </div>
                    <span class="progress-text">{{ job.progress }}%</span>
                  </div>
                </td>
                <td>
                  <span class="worker-badge" v-if="job.worker_id">
                    {{ job.worker_id }}
                  </span>
                  <span v-else class="text-muted">—</span>
                </td>
                <td class="created-date">{{ formatDate(job.created_at) }}</td>
                <td class="actions">
                  <router-link :to="`/queue?job=${job.id}`" class="btn-action" title="View Details">
                    👁️
                  </router-link>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>Unable to load system status</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import api from '@/services/api'

const systemStore = useSystemStore()
const systemStatus = ref<any>(null)
const systemResources = ref<any>({})
const recentJobs = ref<any[]>([])
const loading = ref(true)
const countdown = ref(5)

let refreshInterval: number | null = null
let countdownInterval: number | null = null

const workerUtilization = computed(() => {
  if (!systemStatus.value?.workers?.pool) return 0
  const total = systemStatus.value.workers.pool.total_workers
  if (total === 0) return 0
  return Math.round((systemStatus.value.workers.pool.busy_workers / total) * 100)
})

function queuePercentage(status: string): number {
  if (!systemStatus.value?.queue) return 0
  const total = systemStatus.value.queue.total
  if (total === 0) return 0
  const value = systemStatus.value.queue[status] || 0
  return (value / total) * 100
}

async function loadData() {
  loading.value = true
  try {
    // Load system status
    await systemStore.fetchStatus()
    systemStatus.value = systemStore.status

    // Load system resources
    const resourcesRes = await api.get('/system/resources')
    systemResources.value = resourcesRes.data

    // Load recent jobs
    const jobsRes = await api.get('/jobs?limit=5')
    recentJobs.value = jobsRes.data.jobs || []
  } catch (error: any) {
    console.error('Failed to load dashboard data:', error)
  } finally {
    loading.value = false
  }
}

function formatUptime(seconds: number): string {
  if (!seconds) return '0s'

  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const mins = Math.floor((seconds % 3600) / 60)

  if (days > 0) return `${days}d ${hours}h`
  if (hours > 0) return `${hours}h ${mins}m`
  return `${mins}m`
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '—'

  // Parse the ISO string (backend sends timezone-aware UTC dates)
  const date = new Date(dateStr)

  // Check if date is valid
  if (isNaN(date.getTime())) return 'Invalid date'

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
  return date.toLocaleDateString()
}

function getUsageColor(percent: number): string {
  if (percent < 50) return 'var(--success-color)'
  if (percent < 80) return 'var(--warning-color)'
  return 'var(--danger-color)'
}

function startCountdown() {
  countdown.value = 5
  countdownInterval = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      countdown.value = 5
    }
  }, 1000)
}

onMounted(() => {
  loadData()
  refreshInterval = window.setInterval(loadData, 5000)
  startCountdown()
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
  if (countdownInterval) clearInterval(countdownInterval)
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-xl);
}

.page-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
  background: linear-gradient(135deg, var(--accent-color), var(--primary-color));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.refresh-indicator {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.card {
  background-color: var(--secondary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: transform 0.2s, box-shadow 0.2s;
}

.card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.highlight-card {
  background: linear-gradient(135deg, var(--secondary-bg) 0%, rgba(79, 70, 229, 0.1) 100%);
  border-color: var(--accent-color);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.header-icon {
  font-size: 1.5rem;
  margin-right: var(--spacing-sm);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  flex: 1;
}

.card-body {
  padding: var(--spacing-md);
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm) 0;
}

.stat-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.stat-value {
  color: var(--text-primary);
  font-weight: 600;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.progress-section {
  margin-top: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}

.progress-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: var(--spacing-xs);
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.progress-bar {
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-sm);
  overflow: hidden;
  height: 8px;
}

.progress-bar.large {
  height: 12px;
  border-radius: var(--radius-md);
}

.progress-bar.small {
  height: 6px;
}

.progress-fill {
  height: 100%;
  background-color: var(--accent-color);
  transition: width 0.3s ease, background-color 0.3s ease;
}

.queue-chart {
  margin-top: var(--spacing-md);
  display: flex;
  height: 24px;
  border-radius: var(--radius-sm);
  overflow: hidden;
  background-color: var(--tertiary-bg);
}

.queue-bar {
  transition: width 0.3s ease;
}

.queue-completed {
  background-color: var(--success-color);
}

.queue-processing {
  background-color: var(--accent-color);
}

.queue-queued {
  background-color: var(--warning-color);
}

.queue-failed {
  background-color: var(--danger-color);
}

.resources-section,
.recent-jobs-section {
  margin-bottom: var(--spacing-xl);
}

.section-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.section-icon {
  font-size: 1.75rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.resources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

.resource-card .card-header {
  flex-direction: column;
  align-items: flex-start;
  gap: var(--spacing-xs);
}

.resource-card .card-title {
  font-size: 1rem;
}

.resource-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--accent-color);
  align-self: flex-end;
}

.resource-details {
  margin-top: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.detail-label {
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  font-weight: 600;
}

.empty-gpu {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-muted);
  background-color: var(--secondary-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.table-container {
  overflow-x: auto;
  background-color: var(--secondary-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.jobs-table {
  width: 100%;
  border-collapse: collapse;
}

.jobs-table th,
.jobs-table td {
  padding: var(--spacing-md);
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.jobs-table th {
  background-color: var(--tertiary-bg);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-size: 0.75rem;
}

.jobs-table tbody tr {
  transition: background-color 0.2s;
}

.jobs-table tbody tr:hover {
  background-color: var(--tertiary-bg);
}

.file-name {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-family: monospace;
  font-size: 0.875rem;
}

.file-icon {
  font-size: 1.25rem;
}

.languages {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  font-family: monospace;
}

.lang-badge {
  padding: 2px 6px;
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
}

.arrow {
  color: var(--text-muted);
}

.progress-cell {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.progress-text {
  font-size: 0.75rem;
  color: var(--text-secondary);
  min-width: 40px;
}

.worker-badge {
  padding: 2px 8px;
  background-color: var(--accent-color);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-family: monospace;
}

.created-date {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.actions {
  text-align: center;
}

.btn-action {
  padding: var(--spacing-xs);
  border-radius: var(--radius-sm);
  transition: background-color 0.2s;
  cursor: pointer;
  font-size: 1.25rem;
  text-decoration: none;
}

.btn-action:hover {
  background-color: var(--tertiary-bg);
}


.badge {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-completed {
  background-color: var(--success-color);
  color: var(--primary-bg);
}

.badge-processing {
  background-color: var(--accent-color);
  color: var(--primary-bg);
}

.badge-queued {
  background-color: var(--warning-color);
  color: var(--primary-bg);
}

.badge-failed,
.badge-cancelled {
  background-color: var(--danger-color);
  color: var(--primary-bg);
}

.badge-info {
  background-color: var(--accent-color);
  color: var(--primary-bg);
}

.text-success {
  color: var(--success-color);
}

.text-primary {
  color: var(--accent-color);
}

.text-warning {
  color: var(--warning-color);
}

.text-muted {
  color: var(--text-muted);
}
</style>
