<template>
  <div class="scanner-view">
    <h1 class="page-title">Library Scanner</h1>

    <!-- Notification Toast -->
    <div v-if="notification.show" :class="['notification-toast', `notification-${notification.type}`]">
      <span class="notification-icon">
        <span v-if="notification.type === 'success'">✓</span>
        <span v-else-if="notification.type === 'error'">✕</span>
        <span v-else>ℹ</span>
      </span>
      <span class="notification-message">{{ notification.message }}</span>
      <button @click="notification.show = false" class="notification-close">×</button>
    </div>

    <div v-if="loading" class="spinner"></div>

    <div v-else>
      <!-- Scanner Status Card -->
      <div class="card status-card">
        <div class="card-header">
          <h2 class="card-title">Scanner Status</h2>
          <span :class="['badge', scannerStatus?.is_scanning ? 'badge-processing' : 'badge-queued']">
            {{ scannerStatus?.is_scanning ? 'Scanning' : 'Idle' }}
          </span>
        </div>
        <div class="card-body">
          <div class="status-grid">
            <div class="status-item">
              <span class="status-label">Scheduler:</span>
              <span :class="['badge', scannerStatus?.scheduler_running ? 'badge-completed' : 'badge-cancelled']">
                {{ scannerStatus?.scheduler_running ? 'Running' : 'Stopped' }}
              </span>
            </div>
            <div class="status-item">
              <span class="status-label">File Watcher:</span>
              <span :class="['badge', scannerStatus?.watcher_running ? 'badge-completed' : 'badge-cancelled']">
                {{ scannerStatus?.watcher_running ? 'Active' : 'Inactive' }}
              </span>
            </div>
            <div class="status-item">
              <span class="status-label">Last Scan:</span>
              <span class="status-value">{{ formatDate(scannerStatus?.last_scan_time) }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">Files Scanned:</span>
              <span class="status-value">{{ scannerStatus?.total_files_scanned || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Scanner Controls -->
      <div class="card controls-card">
        <div class="card-header">
          <h2 class="card-title">Scanner Controls</h2>
        </div>
        <div class="card-body">
          <div class="controls-grid">
            <!-- Scheduled Scanning -->
            <div class="control-section">
              <h3 class="control-title">Scheduled Scanning</h3>
              <p class="control-description">Scan library periodically at set intervals</p>
              <div class="control-actions">
                <button
                  v-if="!scannerStatus?.scheduler_running"
                  @click="startScheduler"
                  class="btn btn-primary"
                  :disabled="actionLoading"
                >
                  Start Scheduler
                </button>
                <button
                  v-else
                  @click="stopScheduler"
                  class="btn btn-danger"
                  :disabled="actionLoading"
                >
                  Stop Scheduler
                </button>
              </div>
            </div>

            <!-- File Watcher -->
            <div class="control-section">
              <h3 class="control-title">Real-time File Watcher</h3>
              <p class="control-description">Monitor filesystem for new files</p>
              <div class="control-actions">
                <button
                  v-if="!scannerStatus?.watcher_running"
                  @click="startWatcher"
                  class="btn btn-primary"
                  :disabled="actionLoading"
                >
                  Start Watcher
                </button>
                <button
                  v-else
                  @click="stopWatcher"
                  class="btn btn-danger"
                  :disabled="actionLoading"
                >
                  Stop Watcher
                </button>
              </div>
            </div>

            <!-- Manual Scan -->
            <div class="control-section">
              <h3 class="control-title">Manual Scan</h3>
              <p class="control-description">Scan library immediately</p>
              <div class="control-actions">
                <button
                  @click="showManualScanModal = true"
                  class="btn btn-accent"
                  :disabled="actionLoading || scannerStatus?.is_scanning"
                >
                  Run Manual Scan
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>


      <!-- Library Paths -->
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">Library Paths</h2>
        </div>
        <div class="card-body">
          <div v-if="libraryPaths.length === 0" class="empty-state">
            <p>No library paths configured. Add paths in Settings.</p>
          </div>
          <div v-else class="paths-list">
            <div v-for="(path, index) in libraryPaths" :key="index" class="path-item">
              <span class="path-icon">📁</span>
              <span class="path-text">{{ path }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Scan Results -->
      <div v-if="scanResults.length > 0" class="card">
        <div class="card-header">
          <h2 class="card-title">Recent Scan Results</h2>
        </div>
        <div class="card-body">
          <div class="results-table-container">
            <table class="results-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Files Scanned</th>
                  <th>Matched</th>
                  <th>Jobs Created</th>
                  <th>Skipped</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="result in scanResults" :key="result.id">
                  <td>{{ formatDate(result.timestamp) }}</td>
                  <td>{{ result.files_scanned }}</td>
                  <td class="text-success">{{ result.matched }}</td>
                  <td class="text-primary">{{ result.jobs_created }}</td>
                  <td class="text-muted">{{ result.skipped }}</td>
                  <td>{{ formatDuration(result.duration) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Manual Scan Modal -->
    <div v-if="showManualScanModal" class="modal-overlay" @click="showManualScanModal = false">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>Manual Library Scan</h2>
          <button @click="showManualScanModal = false" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <p>Start a manual scan of all configured library paths?</p>
          <div v-if="libraryPaths.length > 0" class="paths-preview">
            <p class="preview-label">Paths to scan:</p>
            <ul>
              <li v-for="(path, index) in libraryPaths" :key="index">{{ path }}</li>
            </ul>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="runManualScan" class="btn btn-primary" :disabled="actionLoading">
            <span v-if="actionLoading">Scanning...</span>
            <span v-else>Start Scan</span>
          </button>
          <button @click="showManualScanModal = false" class="btn btn-secondary">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import api from '@/services/api'

interface ScannerStatus {
  is_scanning: boolean
  scheduler_running: boolean
  watcher_running: boolean
  last_scan_time: string | null
  total_files_scanned: number
}

interface ScanResult {
  id: number
  timestamp: string
  files_scanned: number
  matched: number
  jobs_created: number
  skipped: number
  duration: number
}

const loading = ref(true)
const actionLoading = ref(false)
const scannerStatus = ref<ScannerStatus | null>(null)
const libraryPaths = ref<string[]>([])
const scanResults = ref<ScanResult[]>([])
const showManualScanModal = ref(false)

// Notification system
const notification = ref<{
  show: boolean
  type: 'success' | 'error' | 'info'
  message: string
}>({
  show: false,
  type: 'info',
  message: ''
})

function showNotification(message: string, type: 'success' | 'error' | 'info' = 'info') {
  notification.value = { show: true, type, message }
  setTimeout(() => {
    notification.value.show = false
  }, 5000)
}

let refreshInterval: number | null = null

async function loadData() {
  loading.value = true
  try {
    // Load scanner status
    const statusRes = await api.get('/scanner/status')
    scannerStatus.value = statusRes.data

    // Load library paths from settings
    try {
      const settingsRes = await api.get('/settings/library_paths')
      const pathsData = settingsRes.data.value

      // Handle both string (comma-separated) and array types
      if (Array.isArray(pathsData)) {
        libraryPaths.value = pathsData.filter((p: string) => p && p.trim())
      } else if (typeof pathsData === 'string' && pathsData.trim()) {
        // Could be JSON array or comma-separated
        try {
          const parsed = JSON.parse(pathsData)
          libraryPaths.value = Array.isArray(parsed) ? parsed : pathsData.split(',').map((p: string) => p.trim()).filter((p: string) => p)
        } catch {
          // Not JSON, treat as comma-separated
          libraryPaths.value = pathsData.split(',').map((p: string) => p.trim()).filter((p: string) => p)
        }
      } else {
        libraryPaths.value = []
      }
    } catch (err) {
      console.error('Failed to load library paths:', err)
      libraryPaths.value = []
    }

    // Load recent scan results (if available)
    // TODO: Implement scan history endpoint
    scanResults.value = []
  } catch (error: any) {
    console.error('Failed to load scanner data:', error)
  } finally {
    loading.value = false
  }
}

async function startScheduler() {
  actionLoading.value = true
  try {
    await api.post('/scanner/scheduler/start')
    await loadData()
    showNotification('Scheduler started successfully', 'success')
  } catch (error: any) {
    showNotification('Failed to start scheduler: ' + (error.response?.data?.detail || error.message), 'error')
  } finally {
    actionLoading.value = false
  }
}

async function stopScheduler() {
  actionLoading.value = true
  try {
    await api.post('/scanner/scheduler/stop')
    await loadData()
    showNotification('Scheduler stopped', 'success')
  } catch (error: any) {
    showNotification('Failed to stop scheduler: ' + (error.response?.data?.detail || error.message), 'error')
  } finally {
    actionLoading.value = false
  }
}

async function startWatcher() {
  actionLoading.value = true
  try {
    await api.post('/scanner/watcher/start')
    await loadData()
    showNotification('File watcher started successfully', 'success')
  } catch (error: any) {
    showNotification('Failed to start watcher: ' + (error.response?.data?.detail || error.message), 'error')
  } finally {
    actionLoading.value = false
  }
}

async function stopWatcher() {
  actionLoading.value = true
  try {
    await api.post('/scanner/watcher/stop')
    await loadData()
    showNotification('File watcher stopped', 'success')
  } catch (error: any) {
    showNotification('Failed to stop watcher: ' + (error.response?.data?.detail || error.message), 'error')
  } finally {
    actionLoading.value = false
  }
}

async function runManualScan() {
  actionLoading.value = true
  try {
    await api.post('/scanner/scan')
    showManualScanModal.value = false
    await loadData()
    showNotification('Manual scan started successfully!', 'success')
  } catch (error: any) {
    showNotification('Failed to start manual scan: ' + (error.response?.data?.detail || error.message), 'error')
  } finally {
    actionLoading.value = false
  }
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return 'Never'

  // Parse the ISO string (backend sends timezone-aware UTC dates)
  const date = new Date(dateStr)

  // Check if date is valid
  if (isNaN(date.getTime())) return 'Invalid date'

  return date.toLocaleString()
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}m ${secs}s`
}

onMounted(() => {
  loadData()
  refreshInterval = window.setInterval(loadData, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.page-title {
  font-size: 2rem;
  margin-bottom: var(--spacing-xl);
  color: var(--text-primary);
}

.status-card {
  margin-bottom: var(--spacing-lg);
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-sm);
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-sm);
}

.status-label {
  font-weight: 600;
  color: var(--text-secondary);
}

.status-value {
  color: var(--text-primary);
}

.controls-card {
  margin-bottom: var(--spacing-lg);
}

.controls-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: var(--spacing-lg);
}

.control-section {
  padding: var(--spacing-md);
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-md);
}

.control-title {
  font-size: 1.125rem;
  margin-bottom: var(--spacing-xs);
  color: var(--text-primary);
}

.control-description {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-bottom: var(--spacing-md);
}

.control-actions {
  display: flex;
  gap: var(--spacing-sm);
}

/* Schedule Configuration Styles */
.schedule-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
  margin-top: var(--spacing-md);
}

.schedule-option {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.schedule-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.schedule-select,
.schedule-input {
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.875rem;
  max-width: 300px;
}

.schedule-select:focus,
.schedule-input:focus {
  outline: none;
  border-color: var(--accent-color);
}

.custom-interval {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--accent-color);
}

.help-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-style: italic;
}

.schedule-preview {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-sm);
}

.preview-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin: 0;
}

.preview-value {
  font-size: 1rem;
  font-weight: 600;
  color: var(--accent-color);
}

.schedule-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.save-indicator {
  color: var(--success-color);
  font-weight: 600;
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.paths-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.path-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-sm);
  font-family: monospace;
}

.path-icon {
  font-size: 1.25rem;
}

.path-text {
  color: var(--text-primary);
}

.results-table-container {
  overflow-x: auto;
}

.results-table {
  width: 100%;
  border-collapse: collapse;
}

.results-table th,
.results-table td {
  padding: var(--spacing-md);
  text-align: left;
  border-bottom: 1px solid var(--border-color);
}

.results-table th {
  background-color: var(--tertiary-bg);
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  font-size: 0.75rem;
}

.text-success {
  color: var(--success-color);
}

.text-primary {
  color: var(--accent-color);
}

.text-muted {
  color: var(--text-muted);
}

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
  max-width: 500px;
  width: 90%;
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

.modal-body {
  padding: var(--spacing-lg);
}

.paths-preview {
  margin-top: var(--spacing-md);
  padding: var(--spacing-md);
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-sm);
}

.preview-label {
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
  color: var(--text-secondary);
}

.paths-preview ul {
  margin: 0;
  padding-left: var(--spacing-lg);
}

.paths-preview li {
  font-family: monospace;
  color: var(--text-primary);
  margin-bottom: var(--spacing-xs);
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
}

.badge {
  display: inline-block;
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

.badge-cancelled {
  background-color: var(--text-muted);
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

/* Notification Toast */
.notification-toast {
  position: fixed;
  top: 80px;
  right: var(--spacing-lg);
  min-width: 300px;
  max-width: 500px;
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  z-index: 9999;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.notification-success {
  background-color: var(--success-color);
  color: white;
}

.notification-error {
  background-color: var(--danger-color);
  color: white;
}

.notification-info {
  background-color: var(--accent-color);
  color: white;
}

.notification-icon {
  font-size: 1.5rem;
  font-weight: bold;
}

.notification-message {
  flex: 1;
  font-size: 0.95rem;
}

.notification-close {
  background: none;
  border: none;
  color: white;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.notification-close:hover {
  opacity: 1;
}
</style>
