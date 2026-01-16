<template>
  <div class="workers-view">
    <div class="page-header">
      <h1 class="page-title">Worker Management</h1>
      <div class="header-actions">
        <button @click="showAddWorkerModal = true" class="btn btn-success">
          ➕ Add Worker
        </button>
        <button @click="refreshWorkers" class="btn btn-secondary" :disabled="loading">
          🔄 Refresh
        </button>
      </div>
    </div>

    <!-- Worker Stats -->
    <div v-if="workersStore.stats" class="card">
      <div class="card-header">
        <h2 class="card-title">Pool Statistics</h2>
      </div>
      <div class="card-body">
        <div class="stats-grid-large">
          <div class="stat-card">
            <div class="stat-icon">👷</div>
            <div class="stat-info">
              <div class="stat-number">{{ workersStore.stats.total_workers }}</div>
              <div class="stat-label">Total Workers</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">💻</div>
            <div class="stat-info">
              <div class="stat-number">{{ workersStore.stats.cpu_workers }}</div>
              <div class="stat-label">CPU Workers</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">🎮</div>
            <div class="stat-info">
              <div class="stat-number">{{ workersStore.stats.gpu_workers }}</div>
              <div class="stat-label">GPU Workers</div>
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-icon">✅</div>
            <div class="stat-info">
              <div class="stat-number text-success">{{ workersStore.stats.total_jobs_completed }}</div>
              <div class="stat-label">Jobs Completed</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Workers List -->
    <div class="card">
      <div class="card-header">
        <h2 class="card-title">Active Workers</h2>
      </div>
      <div class="card-body">
        <div v-if="loading" class="spinner"></div>

        <div v-else-if="workersStore.workers.length === 0" class="empty-state">
          <p>No workers running</p>
          <button @click="showAddWorkerModal = true" class="btn btn-primary">Add First Worker</button>
        </div>

        <table v-else class="table">
          <thead>
            <tr>
              <th>Worker ID</th>
              <th>Type</th>
              <th>Status</th>
              <th>Current Job</th>
              <th>Progress</th>
              <th>Completed</th>
              <th>Failed</th>
              <th>Uptime</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="worker in workersStore.workers" :key="worker.worker_id">
              <td class="worker-id">{{ worker.worker_id }}</td>
              <td>
                <span class="badge" :class="worker.worker_type === 'gpu' ? 'badge-processing' : 'badge-queued'">
                  {{ worker.worker_type.toUpperCase() }}
                  <span v-if="worker.device_id !== null">:{{ worker.device_id }}</span>
                </span>
              </td>
              <td>
                <span class="badge" :class="`badge-${worker.status}`">
                  {{ worker.status }}
                </span>
              </td>
              <td>
                <span v-if="worker.current_job_id" class="job-id">{{ worker.current_job_id.slice(0, 8) }}...</span>
                <span v-else class="text-muted">—</span>
              </td>
              <td>
                <div v-if="worker.current_job_progress > 0" class="progress-container">
                  <div class="progress">
                    <div class="progress-bar" :style="{ width: `${worker.current_job_progress}%` }"></div>
                  </div>
                  <span class="progress-text">{{ worker.current_job_progress.toFixed(1) }}%</span>
                </div>
                <span v-else class="text-muted">—</span>
              </td>
              <td class="text-success">{{ worker.jobs_completed }}</td>
              <td class="text-danger">{{ worker.jobs_failed }}</td>
              <td>{{ formatUptime(worker.uptime_seconds) }}</td>
              <td>
                <button
                  @click="removeWorker(worker.worker_id)"
                  class="btn btn-danger btn-sm"
                  :disabled="worker.status === 'busy'"
                >
                  🗑️ Remove
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add Worker Modal -->
    <div v-if="showAddWorkerModal" class="modal-overlay" @click.self="showAddWorkerModal = false">
      <div class="modal">
        <div class="modal-header">
          <h2>Add Worker</h2>
          <button @click="showAddWorkerModal = false" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Worker Type</label>
            <select v-model="newWorker.worker_type" class="form-control">
              <option value="cpu">CPU</option>
              <option value="gpu" :disabled="!configStore.hasGPU">
                GPU {{ !configStore.hasGPU ? '(Not detected)' : '' }}
              </option>
            </select>
            <span v-if="!configStore.hasGPU" class="warning-text">
              ⚠️ No GPU detected on this system
            </span>
          </div>
          <div v-if="newWorker.worker_type === 'gpu'" class="form-group">
            <label>GPU Device ID</label>
            <input v-model.number="newWorker.device_id" type="number" min="0" class="form-control" />
          </div>
        </div>
        <div class="modal-footer">
          <button @click="showAddWorkerModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="addWorker" class="btn btn-success" :disabled="addingWorker">
            {{ addingWorker ? 'Adding...' : 'Add Worker' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useWorkersStore } from '@/stores/workers'
import { useConfigStore } from '@/stores/config'
import type { AddWorkerRequest } from '@/types/api'

const workersStore = useWorkersStore()
const configStore = useConfigStore()
const loading = ref(true)
const showAddWorkerModal = ref(false)
const addingWorker = ref(false)
const newWorker = ref<AddWorkerRequest>({
  worker_type: 'cpu',
  device_id: 0
})

let refreshInterval: number | null = null

async function loadWorkers() {
  loading.value = true
  try {
    await workersStore.fetchWorkers()
    await workersStore.fetchStats()
  } catch (error) {
    console.error('Failed to load workers:', error)
  } finally {
    loading.value = false
  }
}

async function refreshWorkers() {
  await loadWorkers()
}

async function addWorker() {
  addingWorker.value = true
  try {
    await workersStore.addWorker(newWorker.value)
    showAddWorkerModal.value = false
    // Reset form
    newWorker.value = {
      worker_type: 'cpu',
      device_id: 0
    }
  } catch (error: any) {
    alert('Failed to add worker: ' + (error.message || 'Unknown error'))
  } finally {
    addingWorker.value = false
  }
}

async function removeWorker(workerId: string) {
  if (!confirm(`Are you sure you want to remove worker ${workerId}?`)) {
    return
  }

  try {
    await workersStore.removeWorker(workerId)
  } catch (error: any) {
    alert('Failed to remove worker: ' + (error.message || 'Unknown error'))
  }
}

function formatUptime(seconds: number): string {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  if (hours > 0) return `${hours}h ${minutes}m`
  return `${minutes}m`
}

onMounted(() => {
  loadWorkers()
  // Auto-refresh every 3 seconds
  refreshInterval = window.setInterval(loadWorkers, 3000)
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

.header-actions {
  display: flex;
  gap: var(--spacing-md);
}

.stats-grid-large {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-lg);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-md);
}

.stat-icon {
  font-size: 2.5rem;
}

.stat-info {
  flex: 1;
}

.stat-number {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.worker-id {
  font-family: monospace;
  font-size: 0.875rem;
}

.job-id {
  font-family: monospace;
  font-size: 0.75rem;
  color: var(--accent-color);
}

.progress-container {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.progress {
  flex: 1;
  min-width: 100px;
}

.progress-text {
  font-size: 0.75rem;
  color: var(--text-secondary);
  min-width: 45px;
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-muted);
}

.empty-state p {
  margin-bottom: var(--spacing-md);
  font-size: 1.125rem;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
}

.modal {
  background-color: var(--secondary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
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
  font-size: 1.25rem;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.btn-close:hover {
  background-color: var(--tertiary-bg);
  color: var(--text-primary);
}

.modal-body {
  padding: var(--spacing-lg);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--text-secondary);
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.875rem;
}

.form-control:focus {
  outline: none;
  border-color: var(--accent-color);
}

.warning-text {
  color: var(--warning-color);
  font-size: 0.75rem;
  display: block;
  margin-top: var(--spacing-xs);
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }

  .header-actions {
    width: 100%;
  }

  .header-actions button {
    flex: 1;
  }
}
</style>

