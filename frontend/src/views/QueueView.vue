<template>
  <div class="queue-view">
    <div class="page-header">
      <h1 class="page-title">Job Queue</h1>
      <div class="header-actions">
        <button @click="loadJobs" class="btn btn-secondary" :disabled="loading">
          <span v-if="loading">Loading...</span>
          <span v-else>Refresh</span>
        </button>
        <button @click="clearCompleted" class="btn btn-danger" :disabled="loading || stats.completed === 0">
          Clear Completed
        </button>
      </div>
    </div>

    <!-- Queue Statistics -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-number">{{ stats.total }}</div>
        <div class="stat-label">Total Jobs</div>
      </div>
      <div class="stat-card stat-queued">
        <div class="stat-number">{{ stats.queued }}</div>
        <div class="stat-label">Queued</div>
      </div>
      <div class="stat-card stat-processing">
        <div class="stat-number">{{ stats.processing }}</div>
        <div class="stat-label">Processing</div>
      </div>
      <div class="stat-card stat-completed">
        <div class="stat-number">{{ stats.completed }}</div>
        <div class="stat-label">Completed</div>
      </div>
      <div class="stat-card stat-failed">
        <div class="stat-number">{{ stats.failed }}</div>
        <div class="stat-label">Failed</div>
      </div>
    </div>

    <div v-if="loading && jobs.length === 0" class="spinner"></div>

    <div v-else>
      <!-- 1. PROCESSING NOW TABLE -->
      <div v-if="processingJobs.length > 0" class="section-container">
        <h2 class="section-title">🔄 Processing Now</h2>

        <!-- Transcription/Translation Jobs Processing -->
        <div v-if="processingTranscriptionJobs.length > 0" class="subsection">
          <h3 class="subsection-title">📝 Transcription & Translation</h3>
          <div class="jobs-table-container">
            <table class="jobs-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>File</th>
                  <th>Languages</th>
                  <th>Task</th>
                  <th>Priority</th>
                  <th>Progress</th>
                  <th>Worker</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="job in processingTranscriptionJobs" :key="job.id" class="row-processing">
                  <td class="id-cell">#{{ job.id }}</td>
                  <td class="file-cell">
                    <div class="file-name" :title="job.file_path">{{ getFileName(job.file_path) }}</div>
                    <div class="file-path">{{ getFilePath(job.file_path) }}</div>
                  </td>
                  <td class="language-cell">{{ job.source_lang }} → {{ job.target_lang }}</td>
                  <td class="task-cell">{{ job.transcribe_or_translate || 'transcribe' }}</td>
                  <td class="text-center priority-cell">
                    <span :class="getPriorityClass(job.priority)">{{ job.priority }}</span>
                  </td>
                  <td class="progress-cell">
                    <div class="progress-container">
                      <div class="progress-bar-inline">
                        <div class="progress-fill" :style="{ width: (job.progress || 0) + '%' }"></div>
                      </div>
                      <span class="progress-text">{{ (job.progress || 0).toFixed(1) }}%</span>
                    </div>
                  </td>
                  <td class="worker-cell">
                    <span v-if="job.worker_id" class="worker-badge">{{ job.worker_id }}</span>
                  </td>
                  <td class="actions-cell">
                    <div class="action-buttons">
                      <button @click="cancelJob(job.id)" class="btn-action btn-cancel" title="Cancel">✕</button>
                      <button @click="viewJobDetails(job)" class="btn-action btn-view" title="View Details">ℹ</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Language Detection Jobs Processing -->
        <div v-if="processingDetectionJobs.length > 0" class="subsection">
          <h3 class="subsection-title">🔍 Language Detection</h3>
          <div class="jobs-table-container">
            <table class="jobs-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>File</th>
                  <th>Priority</th>
                  <th>Progress</th>
                  <th>Worker</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="job in processingDetectionJobs" :key="job.id" class="row-processing">
                  <td class="id-cell">#{{ job.id }}</td>
                  <td class="file-cell">
                    <div class="file-name" :title="job.file_path">{{ getFileName(job.file_path) }}</div>
                    <div class="file-path">{{ getFilePath(job.file_path) }}</div>
                  </td>
                  <td class="text-center priority-cell">
                    <span :class="getPriorityClass(job.priority)">{{ job.priority }}</span>
                  </td>
                  <td class="progress-cell">
                    <div class="progress-container">
                      <div class="progress-bar-inline">
                        <div class="progress-fill" :style="{ width: (job.progress || 0) + '%' }"></div>
                      </div>
                      <span class="progress-text">{{ (job.progress || 0).toFixed(1) }}%</span>
                    </div>
                  </td>
                  <td class="worker-cell">
                    <span v-if="job.worker_id" class="worker-badge">{{ job.worker_id }}</span>
                  </td>
                  <td class="actions-cell">
                    <div class="action-buttons">
                      <button @click="cancelJob(job.id)" class="btn-action btn-cancel" title="Cancel">✕</button>
                      <button @click="viewJobDetails(job)" class="btn-action btn-view" title="View Details">ℹ</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- 2. MULTI-PURPOSE TABLE WITH TABS -->
      <div class="section-container">
        <div class="tabs-container">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="['tab-button', { 'tab-active': activeTab === tab.id }]"
          >
            {{ tab.label }}
            <span class="tab-count">{{ tab.count }}</span>
          </button>
        </div>

        <!-- Search Filter -->
        <div class="filters-bar">
          <div class="filter-group">
            <label>Search:</label>
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Search by filename..."
              class="filter-input"
            />
          </div>
        </div>

        <!-- Tab Content -->
        <div v-if="currentTabJobs.length === 0" class="empty-state">
          <p>No jobs in this category.</p>
        </div>

        <div v-else class="jobs-table-container">
          <table class="jobs-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>File</th>
                <th>Status</th>
                <th v-if="activeTab === 'completed_detection'">Detected Language</th>
                <th v-if="activeTab !== 'queued_detection' && activeTab !== 'completed_detection'">Languages</th>
                <th v-if="activeTab !== 'queued_detection' && activeTab !== 'completed_detection'">Task</th>
                <th>Priority</th>
                <th>Created</th>
                <th v-if="activeTab === 'completed' || activeTab === 'completed_detection'">Completed</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="job in paginatedTabJobs" :key="job.id" :class="'row-' + job.status">
                <td class="id-cell">#{{ job.id }}</td>
                <td class="type-cell">
                  <span v-if="job.job_type === 'language_detection'" class="job-type-badge badge-detection">
                    🔍 DETECT
                  </span>
                  <span v-else class="job-type-badge badge-transcription">
                    📝 TRANS
                  </span>
                </td>
                <td class="file-cell">
                  <div class="file-name" :title="job.file_path">{{ getFileName(job.file_path) }}</div>
                  <div class="file-path">{{ getFilePath(job.file_path) }}</div>
                </td>
                <td>
                  <span :class="['badge', 'badge-' + job.status]">{{ job.status }}</span>
                </td>
                <td v-if="activeTab === 'completed_detection'" class="language-cell detected-lang">
                  <span class="detected-badge">{{ getDetectedLanguage(job) }}</span>
                </td>
                <td v-if="activeTab !== 'queued_detection' && activeTab !== 'completed_detection'" class="language-cell">
                  {{ job.source_lang }} → {{ job.target_lang }}
                </td>
                <td v-if="activeTab !== 'queued_detection' && activeTab !== 'completed_detection'" class="task-cell">
                  <span v-if="job.job_type === 'language_detection'">detect</span>
                  <span v-else>{{ job.transcribe_or_translate || 'transcribe' }}</span>
                </td>
                <td class="text-center priority-cell">
                  <span :class="getPriorityClass(job.priority)">{{ job.priority }}</span>
                </td>
                <td class="date-cell">{{ formatDate(job.created_at) }}</td>
                <td v-if="activeTab === 'completed' || activeTab === 'completed_detection'" class="date-cell">
                  {{ formatDate(job.completed_at || null) }}
                </td>
                <td class="actions-cell">
                  <div class="action-buttons">
                    <button
                      v-if="job.status === 'failed'"
                      @click="retryJob(job.id)"
                      class="btn-action btn-retry"
                      title="Retry"
                    >↻</button>
                    <button
                      v-if="job.status === 'queued'"
                      @click="cancelJob(job.id)"
                      class="btn-action btn-cancel"
                      title="Cancel"
                    >✕</button>
                    <button
                      @click="viewJobDetails(job)"
                      class="btn-action btn-view"
                      title="View Details"
                    >ℹ</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div v-if="totalTabPages > 1" class="pagination">
          <button
            @click="currentTabPage--"
            :disabled="currentTabPage === 1"
            class="btn btn-secondary btn-sm"
          >
            Previous
          </button>

          <span class="pagination-info">
            Page {{ currentTabPage }} of {{ totalTabPages }} ({{ currentTabJobs.length }} jobs)
          </span>

          <button
            @click="currentTabPage++"
            :disabled="currentTabPage === totalTabPages"
            class="btn btn-secondary btn-sm"
          >
            Next
          </button>
        </div>
      </div>
    </div>

    <!-- Job Details Modal -->
    <div v-if="selectedJob" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Job Details #{{ selectedJob.id }}</h2>
          <button @click="closeModal" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="detail-row">
            <span class="detail-label">Job Type:</span>
            <span class="detail-value">
              <span v-if="selectedJob.job_type === 'language_detection'" class="job-type-badge badge-detection">
                🔍 Language Detection
              </span>
              <span v-else class="job-type-badge badge-transcription">
                📝 Transcription
              </span>
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Status:</span>
            <span :class="['badge', 'badge-' + selectedJob.status]">{{ selectedJob.status }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">File Path:</span>
            <span class="detail-value">{{ selectedJob.file_path }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Source Language:</span>
            <span class="detail-value">{{ selectedJob.source_lang }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Target Language:</span>
            <span class="detail-value">{{ selectedJob.target_lang }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Task Type:</span>
            <span class="detail-value">
              <span v-if="selectedJob.job_type === 'language_detection'">detect</span>
              <span v-else>{{ selectedJob.transcribe_or_translate || 'transcribe' }}</span>
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Priority:</span>
            <span class="detail-value">{{ selectedJob.priority }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Worker ID:</span>
            <span class="detail-value">{{ selectedJob.worker_id || 'Not assigned' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Progress:</span>
            <span class="detail-value">{{ selectedJob.progress || 0 }}%</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Created:</span>
            <span class="detail-value">{{ new Date(selectedJob.created_at).toLocaleString() }}</span>
          </div>
          <div v-if="selectedJob.started_at" class="detail-row">
            <span class="detail-label">Started:</span>
            <span class="detail-value">{{ new Date(selectedJob.started_at).toLocaleString() }}</span>
          </div>
          <div v-if="selectedJob.completed_at" class="detail-row">
            <span class="detail-label">Completed:</span>
            <span class="detail-value">{{ new Date(selectedJob.completed_at).toLocaleString() }}</span>
          </div>
          <div v-if="selectedJob.error_message" class="detail-row">
            <span class="detail-label">Error:</span>
            <span class="detail-value error-text">{{ selectedJob.error_message }}</span>
          </div>
        </div>
        <div class="modal-footer">
          <button
            v-if="selectedJob.status === 'failed'"
            @click="retryJob(selectedJob.id); closeModal()"
            class="btn btn-primary"
          >
            Retry Job
          </button>
          <button @click="closeModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '@/services/api'

interface Job {
  id: number
  file_path: string
  job_type: 'transcription' | 'language_detection'
  status: string
  source_lang: string
  target_lang: string
  transcribe_or_translate?: string
  priority: number
  progress?: number
  worker_id?: string
  created_at: string
  started_at?: string
  completed_at?: string
  error_message?: string
  srt_content?: string
}

const jobs = ref<Job[]>([])
const loading = ref(false)
const selectedJob = ref<Job | null>(null)

const activeTab = ref('queued')
const searchQuery = ref('')

const currentTabPage = ref(1)
const itemsPerPage = 20

let refreshInterval: number | null = null

const stats = computed(() => {
  return {
    total: jobs.value.length,
    queued: jobs.value.filter(j => j.status === 'queued').length,
    processing: jobs.value.filter(j => j.status === 'processing').length,
    completed: jobs.value.filter(j => j.status === 'completed').length,
    failed: jobs.value.filter(j => j.status === 'failed').length,
  }
})

// Processing jobs
const processingJobs = computed(() => {
  return jobs.value.filter(j => j.status === 'processing')
})

const processingTranscriptionJobs = computed(() => {
  return processingJobs.value.filter(j => j.job_type === 'transcription')
})

const processingDetectionJobs = computed(() => {
  return processingJobs.value.filter(j => j.job_type === 'language_detection')
})

// Tabs configuration
const tabs = computed(() => {
  const queuedTranscription = jobs.value.filter(j => j.status === 'queued' && j.job_type === 'transcription').length
  const queuedDetection = jobs.value.filter(j => j.status === 'queued' && j.job_type === 'language_detection').length
  const completedTranscription = jobs.value.filter(j => j.status === 'completed' && j.job_type === 'transcription').length
  const completedDetection = jobs.value.filter(j => j.status === 'completed' && j.job_type === 'language_detection').length
  const failed = jobs.value.filter(j => j.status === 'failed').length

  return [
    { id: 'queued', label: '📋 Queued Jobs', count: queuedTranscription },
    { id: 'queued_detection', label: '🔍 Queued Detections', count: queuedDetection },
    { id: 'completed', label: '✅ Completed Jobs', count: completedTranscription },
    { id: 'completed_detection', label: '✅ Completed Detections', count: completedDetection },
    { id: 'failed', label: '❌ Failed Jobs', count: failed },
  ]
})

// Current tab jobs
const currentTabJobs = computed(() => {
  let filtered: Job[] = []

  switch (activeTab.value) {
    case 'queued':
      filtered = jobs.value.filter(j => j.status === 'queued' && j.job_type === 'transcription')
      break
    case 'queued_detection':
      filtered = jobs.value.filter(j => j.status === 'queued' && j.job_type === 'language_detection')
      break
    case 'completed':
      filtered = jobs.value.filter(j => j.status === 'completed' && j.job_type === 'transcription')
      break
    case 'completed_detection':
      filtered = jobs.value.filter(j => j.status === 'completed' && j.job_type === 'language_detection')
      break
    case 'failed':
      filtered = jobs.value.filter(j => j.status === 'failed')
      break
    default:
      filtered = jobs.value
  }

  // Apply search filter
  if (searchQuery.value) {
    const search = searchQuery.value.toLowerCase()
    filtered = filtered.filter(j => j.file_path.toLowerCase().includes(search))
  }

  return filtered
})

const totalTabPages = computed(() => {
  return Math.ceil(currentTabJobs.value.length / itemsPerPage)
})

const paginatedTabJobs = computed(() => {
  const start = (currentTabPage.value - 1) * itemsPerPage
  const end = start + itemsPerPage
  return currentTabJobs.value.slice(start, end)
})

async function loadJobs() {
  loading.value = true
  try {
    const response = await api.get('/jobs')
    jobs.value = response.data.jobs || []
  } catch (error: any) {
    console.error('Failed to load jobs:', error)
  } finally {
    loading.value = false
  }
}

async function retryJob(jobId: number) {
  try {
    await api.post(`/jobs/${jobId}/retry`)
    await loadJobs()
  } catch (error: any) {
    console.error('Failed to retry job:', error)
    alert('Failed to retry job: ' + (error.response?.data?.detail || error.message))
  }
}

async function cancelJob(jobId: number) {
  if (!confirm('Are you sure you want to cancel this job?')) return

  try {
    await api.post(`/jobs/${jobId}/cancel`)
    await loadJobs()
  } catch (error: any) {
    console.error('Failed to cancel job:', error)
    alert('Failed to cancel job: ' + (error.response?.data?.detail || error.message))
  }
}

async function clearCompleted() {
  if (!confirm('Clear all completed jobs?')) return

  try {
    await api.delete('/jobs/completed')
    await loadJobs()
  } catch (error: any) {
    console.error('Failed to clear completed jobs:', error)
    alert('Failed to clear jobs: ' + (error.response?.data?.detail || error.message))
  }
}


function viewJobDetails(job: Job) {
  selectedJob.value = job
}

function closeModal() {
  selectedJob.value = null
}

function getFileName(path: string): string {
  if (!path) return 'Unknown'
  const parts = path.split('/')
  return parts[parts.length - 1]
}

function getFilePath(path: string): string {
  if (!path) return ''
  const parts = path.split('/')
  parts.pop() // Remove filename
  return parts.join('/')
}

function getPriorityClass(priority: number): string {
  if (priority >= 10) return 'priority-high'
  if (priority >= 5) return 'priority-medium'
  return 'priority-low'
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'Never'

  // Parse the ISO string (backend sends timezone-aware UTC dates)
  const date = new Date(dateStr)

  // Check if date is valid
  if (isNaN(date.getTime())) return 'Invalid date'

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`

  // For older dates, show local date and time
  return date.toLocaleString()
}

function getDetectedLanguage(job: Job): string {
  // Try to extract from srt_content field
  // Detection jobs store result as:
  // "Language detected: ja (Japanese)\nConfidence: 99%"
  if (job.srt_content && job.srt_content !== 'None' && job.srt_content !== 'null') {
    const lines = job.srt_content.split('\n')
    if (lines.length > 0 && lines[0].includes('Language detected:')) {
      // Extract language code and name
      const match = lines[0].match(/Language detected:\s*(\w+)\s*\(([^)]+)\)/)
      if (match) {
        const langCode = match[1].toUpperCase()
        const langName = match[2]

        // Extract confidence from second line if available
        let confidence = ''
        if (lines.length > 1 && lines[1].includes('Confidence:')) {
          const confMatch = lines[1].match(/Confidence:\s*(\d+)%/)
          if (confMatch) {
            confidence = ` (${confMatch[1]}%)`
          }
        }

        return `${langName}${confidence}`
      }
    }
  }

  // Fallback: If source_lang is set and not None/null, use it
  if (job.source_lang && job.source_lang !== 'None' && job.source_lang !== 'null') {
    return job.source_lang.toUpperCase()
  }

  return 'Unknown'
}

onMounted(() => {
  loadJobs()
  refreshInterval = window.setInterval(loadJobs, 3000) // Refresh every 3 seconds
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
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
  font-size: 2rem;
  color: var(--text-primary);
  margin: 0;
}

.header-actions {
  display: flex;
  gap: var(--spacing-md);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

/* Section Containers */
.section-container {
  margin-bottom: var(--spacing-xl);
  background-color: var(--secondary-bg);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  border: 1px solid var(--border-color);
}

.section-title {
  font-size: 1.5rem;
  color: var(--text-primary);
  margin: 0 0 var(--spacing-lg) 0;
  font-weight: 600;
}

.subsection {
  margin-bottom: var(--spacing-lg);
}

.subsection:last-child {
  margin-bottom: 0;
}

.subsection-title {
  font-size: 1.1rem;
  color: var(--text-secondary);
  margin: 0 0 var(--spacing-md) 0;
  font-weight: 600;
  padding-bottom: var(--spacing-sm);
  border-bottom: 2px solid var(--border-color);
}

/* Tabs */
.tabs-container {
  display: flex;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-lg);
  overflow-x: auto;
  border-bottom: 2px solid var(--border-color);
}

.tab-button {
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 600;
  white-space: nowrap;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
}

.tab-button:hover {
  color: var(--text-primary);
  background-color: var(--tertiary-bg);
}

.tab-button.tab-active {
  color: var(--accent-color);
  border-bottom-color: var(--accent-color);
}

.tab-count {
  display: inline-block;
  background-color: var(--tertiary-bg);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  min-width: 20px;
  text-align: center;
}

.tab-button.tab-active .tab-count {
  background-color: var(--accent-color);
  color: var(--primary-bg);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.stat-card {
  background-color: var(--secondary-bg);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  text-align: center;
  border: 2px solid var(--border-color);
}

.stat-card.stat-queued {
  border-color: var(--warning-color);
}

.stat-card.stat-processing {
  border-color: var(--accent-color);
}

.stat-card.stat-completed {
  border-color: var(--success-color);
}

.stat-card.stat-failed {
  border-color: var(--danger-color);
}

.stat-number {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-muted);
  text-transform: uppercase;
}

/* Filters */
.filters-bar {
  display: flex;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-md);
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex: 1;
}

.filter-group label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 600;
}

.filter-input {
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--secondary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.875rem;
  flex: 1;
  min-width: 200px;
}

/* Jobs Table */
.jobs-table-container {
  overflow-x: auto;
  background-color: var(--secondary-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  margin-bottom: var(--spacing-lg);
}

.jobs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.jobs-table thead {
  background-color: var(--tertiary-bg);
  position: sticky;
  top: 0;
}

.jobs-table th {
  padding: var(--spacing-md);
  text-align: left;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.5px;
  border-bottom: 2px solid var(--border-color);
}

.jobs-table td {
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
}

.jobs-table tbody tr:last-child td {
  border-bottom: none;
}

.jobs-table tbody tr:hover {
  background-color: var(--tertiary-bg);
}

.row-processing {
  background-color: rgba(74, 144, 226, 0.05);
}

.row-failed {
  background-color: rgba(231, 76, 60, 0.05);
}

.id-cell {
  font-family: monospace;
  color: var(--text-muted);
  font-weight: 600;
}

.file-cell {
  max-width: 250px;
}

.file-name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-path {
  font-size: 0.75rem;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.language-cell {
  font-family: monospace;
  font-size: 0.875rem;
}

.detected-lang {
  font-weight: 500;
}

.detected-badge {
  display: inline-block;
  background-color: #ff9500;
  color: var(--primary-bg);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-family: 'Segoe UI', sans-serif;
  font-size: 0.875rem;
  font-weight: 600;
  border: 1px solid #cc7700;
}

.task-cell {
  text-transform: capitalize;
  color: var(--text-secondary);
}

.text-center {
  text-align: center;
}

.priority-cell {
  font-weight: 600;
}

.priority-high {
  color: var(--danger-color);
}

.priority-medium {
  color: var(--warning-color);
}

.priority-low {
  color: var(--text-muted);
}

.progress-cell {
  min-width: 120px;
}

.progress-container {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.progress-bar-inline {
  flex: 1;
  height: 8px;
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: var(--accent-color);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  min-width: 35px;
}

.worker-cell {
  font-size: 0.75rem;
}

.worker-badge {
  background-color: var(--tertiary-bg);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-family: monospace;
}

.date-cell {
  min-width: 100px;
}

.date-main {
  color: var(--text-primary);
}

.date-sub {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 2px;
}

.actions-cell {
  min-width: 100px;
}

.action-buttons {
  display: flex;
  gap: var(--spacing-xs);
}

.btn-action {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  background-color: var(--tertiary-bg);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
}

.btn-action:hover {
  background-color: var(--secondary-bg);
  transform: scale(1.1);
}

.btn-retry {
  color: var(--accent-color);
}

.btn-cancel {
  color: var(--danger-color);
}

.btn-view {
  color: var(--text-secondary);
}

/* Badges */
.badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-queued {
  background-color: var(--warning-color);
  color: var(--primary-bg);
}

.badge-processing {
  background-color: var(--accent-color);
  color: var(--primary-bg);
}

.badge-completed {
  background-color: var(--success-color);
  color: var(--primary-bg);
}

.badge-failed {
  background-color: var(--danger-color);
  color: var(--text-primary);
}

.badge-cancelled {
  background-color: var(--text-muted);
  color: var(--primary-bg);
}

/* Job Type Badges */
.type-cell {
  min-width: 100px;
}

.job-type-badge {
  display: inline-block;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  white-space: nowrap;
}

.badge-detection {
  background-color: #ff9500;
  color: var(--primary-bg);
  border: 1px solid #cc7700;
}

.badge-transcription {
  background-color: #0066cc;
  color: var(--text-primary);
  border: 1px solid #0052a3;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
}

.pagination-info {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: var(--secondary-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--border-color);
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
}

.btn-close:hover {
  color: var(--text-primary);
}

.modal-body {
  padding: var(--spacing-lg);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--border-color);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-weight: 600;
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  text-align: right;
}

.error-text {
  color: var(--danger-color);
  font-family: monospace;
  font-size: 0.875rem;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-muted);
  background-color: var(--secondary-bg);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.text-muted {
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .filters-bar {
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .filter-group {
    width: 100%;
  }

  .filter-select,
  .filter-input {
    flex: 1;
  }

  .jobs-table {
    font-size: 0.75rem;
  }

  .jobs-table th,
  .jobs-table td {
    padding: var(--spacing-sm);
  }

  .file-cell {
    max-width: 150px;
  }
}
</style>
