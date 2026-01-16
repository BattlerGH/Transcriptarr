<template>
  <div class="settings-view">
    <div class="page-header">
      <h1 class="page-title">Settings</h1>
      <div class="header-actions">
        <button @click="loadSettings" class="btn btn-secondary" :disabled="loading">
          <span v-if="loading">Loading...</span>
          <span v-else>↻ Refresh</span>
        </button>
        <button @click="saveSettings" class="btn btn-primary" :disabled="saving || !hasChanges">
          <span v-if="saving">Saving...</span>
          <span v-else>💾 Save Changes</span>
        </button>
      </div>
    </div>

    <div v-if="loading" class="spinner"></div>

    <div v-else class="settings-container">
      <!-- General Settings -->
      <div class="card settings-card">
        <div class="card-header">
          <h2 class="card-title">🔧 General Settings</h2>
        </div>
        <div class="card-body">
          <div class="settings-grid">
            <div class="setting-item full-width">
              <label class="setting-label">
                Operation Mode
                <span class="setting-description">Standalone or Bazarr provider mode (requires restart)</span>
              </label>
              <select v-model="settings.operation_mode" class="setting-input" @change="markChanged">
                <option value="standalone">Standalone</option>
                <option value="bazarr_slave">Bazarr Provider</option>
              </select>
            </div>

            <!-- Library Paths - Solo en modo Standalone -->
            <div v-if="isStandalone" class="setting-item full-width">
              <label class="setting-label">
                Library Paths
                <span class="setting-description">Media library folders to scan</span>
              </label>
              <div class="paths-list">
                <div v-for="(path, index) in libraryPaths" :key="index" class="path-display">
                  <code class="path-code">{{ path }}</code>
                  <button @click="removePath(index)" class="btn-icon">🗑️</button>
                </div>
                <button @click="showPathBrowser = true" class="btn btn-secondary btn-sm">
                  📁 Browse for Path
                </button>
              </div>
            </div>

            <div class="setting-item">
              <label class="setting-label">
                Log Level
                <span class="setting-description">Application logging level</span>
              </label>
              <select v-model="settings.log_level" class="setting-input" @change="markChanged">
                <option value="DEBUG">DEBUG</option>
                <option value="INFO">INFO</option>
                <option value="WARNING">WARNING</option>
                <option value="ERROR">ERROR</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <!-- Worker Settings -->
      <div class="card settings-card">
        <div class="card-header">
          <h2 class="card-title">⚙️ Worker Settings</h2>
        </div>
        <div class="card-body">
          <div class="settings-grid">
            <div class="setting-item">
              <label class="setting-label">
                CPU Workers on Startup
                <span class="setting-description">Number of CPU workers to start automatically</span>
              </label>
              <input
                type="number"
                v-model.number="settings.worker_cpu_count"
                class="setting-input"
                min="0"
                max="16"
                @input="markChanged"
              />
            </div>

            <div class="setting-item">
              <label class="setting-label">
                GPU Workers on Startup
                <span class="setting-description">Number of GPU workers to start automatically</span>
              </label>
              <input
                type="number"
                v-model.number="settings.worker_gpu_count"
                class="setting-input"
                min="0"
                max="8"
                :disabled="!hasGPU"
                :placeholder="hasGPU ? '0' : 'No GPU detected'"
                @input="markChanged"
              />
              <span v-if="!hasGPU" class="warning-message">
                ⚠️ No GPU detected - GPU workers will not start
              </span>
            </div>

            <div class="setting-item">
              <label class="setting-label">
                Health Check Interval
                <span class="setting-description">Worker health check interval (seconds)</span>
              </label>
              <input
                type="number"
                v-model.number="settings.worker_healthcheck_interval"
                class="setting-input"
                min="10"
                max="300"
                @input="markChanged"
              />
            </div>

            <div class="setting-item">
              <label class="setting-label">
                Auto-Restart Failed Workers
                <span class="setting-description">Automatically restart workers that crash</span>
              </label>
              <label class="toggle-switch">
                <input
                  type="checkbox"
                  v-model="settings.worker_auto_restart"
                  @change="markChanged"
                />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Transcription Settings -->
      <div class="card settings-card">
        <div class="card-header">
          <h2 class="card-title">🎤 Transcription Settings</h2>
        </div>
        <div class="card-body">
          <div class="settings-grid">
            <div class="setting-item">
              <label class="setting-label">
                Whisper Model
                <span class="setting-description">AI model size (larger = better quality, slower)</span>
              </label>
              <select v-model="settings.whisper_model" class="setting-input" @change="markChanged">
                <option value="tiny">Tiny (fastest)</option>
                <option value="base">Base</option>
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large">Large</option>
                <option value="large-v2">Large v2</option>
                <option value="large-v3">Large v3 (best)</option>
              </select>
            </div>

            <div class="setting-item">
              <label class="setting-label">
                CPU Compute Type
                <span class="setting-description">Precision for CPU workers</span>
              </label>
              <select v-model="settings.cpu_compute_type" class="setting-input" @change="markChanged">
                <option value="auto">Auto (recommended)</option>
                <option value="int8">Int8 (faster, lower quality)</option>
                <option value="float32">Float32 (slower, better quality)</option>
              </select>
            </div>

            <div class="setting-item" v-if="hasGPU">
              <label class="setting-label">
                GPU Compute Type
                <span class="setting-description">Precision for GPU workers</span>
              </label>
              <select v-model="settings.gpu_compute_type" class="setting-input" @change="markChanged">
                <option value="auto">Auto (recommended)</option>
                <option value="float16">Float16 (fast, recommended)</option>
                <option value="float32">Float32 (slower, more precise)</option>
                <option value="int8_float16">Int8 + Float16 (fastest, lower quality)</option>
                <option value="int8">Int8 (very fast, lowest quality)</option>
              </select>
            </div>

            <div class="setting-item full-width">
              <label class="setting-label">
                Skip if Subtitle Exists
                <span class="setting-description">Skip transcription if subtitle file already exists</span>
              </label>
              <label class="toggle-switch">
                <input
                  type="checkbox"
                  v-model="settings.skip_if_exists"
                  @change="markChanged"
                />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Scanner Settings - Solo en modo Standalone -->
      <div v-if="isStandalone" class="card settings-card">
        <div class="card-header">
          <h2 class="card-title">🔍 Scanner Settings</h2>
        </div>
        <div class="card-body">
          <div class="settings-grid">
            <div class="setting-item full-width">
              <label class="setting-label">
                Enable Library Scanner
                <span class="setting-description">Automatically scan libraries for new media</span>
              </label>
              <label class="toggle-switch">
                <input
                  type="checkbox"
                  v-model="settings.scanner_enabled"
                  @change="markChanged"
                />
                <span class="toggle-slider"></span>
              </label>
            </div>

            <div class="setting-item full-width">
              <label class="setting-label">
                Scan Interval
                <span class="setting-description">How often should the scanner run automatically</span>
              </label>
              <div class="interval-config">
                <select v-model="scanInterval" class="setting-input" @change="handleIntervalChange">
                  <option :value="15">Every 15 minutes</option>
                  <option :value="30">Every 30 minutes</option>
                  <option :value="60">Every hour</option>
                  <option :value="120">Every 2 hours</option>
                  <option :value="180">Every 3 hours</option>
                  <option :value="360">Every 6 hours (recommended)</option>
                  <option :value="720">Every 12 hours</option>
                  <option :value="1440">Every 24 hours (daily)</option>
                  <option value="custom">Custom...</option>
                </select>

                <div v-if="scanInterval === 'custom'" class="custom-interval-input">
                  <input
                    type="number"
                    v-model.number="customScanInterval"
                    class="setting-input"
                    min="1"
                    max="10080"
                    placeholder="Minutes"
                    @input="handleCustomIntervalChange"
                  />
                  <span class="help-text">Between 1 minute and 7 days (10080 minutes)</span>
                </div>

                <div class="interval-preview">
                  <span class="preview-icon">📅</span>
                  <span class="preview-text">
                    Scans will run approximately every: <strong>{{ getScanIntervalText() }}</strong>
                  </span>
                </div>
              </div>
            </div>

            <div class="setting-item full-width">
              <label class="setting-label">
                Enable File Watcher
                <span class="setting-description">Watch for new files in real-time</span>
              </label>
              <label class="toggle-switch">
                <input
                  type="checkbox"
                  v-model="settings.watcher_enabled"
                  @change="markChanged"
                />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Bazarr Provider Settings - Solo en modo Bazarr -->
      <div v-if="!isStandalone" class="card settings-card">
        <div class="card-header">
          <h2 class="card-title">🔌 Bazarr Provider Settings</h2>
        </div>
        <div class="card-body">
          <div class="settings-grid">
            <div class="setting-item full-width">
              <label class="setting-label">
                Provider Enabled
                <span class="setting-description">Enable Bazarr provider API</span>
              </label>
              <label class="toggle-switch">
                <input
                  type="checkbox"
                  v-model="settings.bazarr_provider_enabled"
                  @change="markChanged"
                />
                <span class="toggle-slider"></span>
              </label>
            </div>

            <div v-if="bazarrApiKey" class="setting-item full-width">
              <label class="setting-label">
                API Key
                <span class="setting-description">Use this key to configure Bazarr</span>
              </label>
              <div class="copy-field">
                <code>{{ bazarrApiKey }}</code>
                <button @click="copyToClipboard(bazarrApiKey)" class="btn-icon">📋</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Path Browser Modal -->
    <div v-if="showPathBrowser" class="modal-overlay" @click.self="showPathBrowser = false">
      <PathBrowser @select="addPath" @close="showPathBrowser = false" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'
import PathBrowser from '@/components/PathBrowser.vue'
import axios from 'axios'

const configStore = useConfigStore()

const loading = ref(true)
const saving = ref(false)
const hasChanges = ref(false)
const showPathBrowser = ref(false)

// Settings
const settings = ref({
  operation_mode: 'standalone',
  log_level: 'INFO',
  worker_cpu_count: 0,
  worker_gpu_count: 0,
  worker_healthcheck_interval: 30,
  worker_auto_restart: true,
  whisper_model: 'large-v3',
  cpu_compute_type: 'auto',
  gpu_compute_type: 'auto',
  skip_if_exists: true,
  scanner_enabled: false,
  scanner_cron: '0 2 * * *',
  watcher_enabled: false,
  bazarr_provider_enabled: false
})

const libraryPaths = ref<string[]>([])
const bazarrApiKey = ref('')

// Scanner interval configuration
const scanInterval = ref<number | 'custom'>(360) // Default: 6 hours
const customScanInterval = ref(90)

const hasGPU = computed(() => configStore.hasGPU)
const isStandalone = computed(() => settings.value.operation_mode === 'standalone')

function markChanged() {
  hasChanges.value = true
}

async function loadSettings() {
  loading.value = true
  hasChanges.value = false

  try {
    const response = await axios.get('/api/settings')
    const settingsMap: Record<string, any> = {}

    response.data.forEach((setting: any) => {
      settingsMap[setting.key] = setting.value
    })

    // Parse settings
    settings.value.operation_mode = settingsMap['operation_mode'] || 'standalone'
    settings.value.log_level = settingsMap['log_level'] || 'INFO'
    settings.value.worker_cpu_count = parseInt(settingsMap['worker_cpu_count'] || '0')
    // Force GPU worker count to 0 if no GPU detected
    settings.value.worker_gpu_count = hasGPU.value ? parseInt(settingsMap['worker_gpu_count'] || '0') : 0
    settings.value.worker_healthcheck_interval = parseInt(settingsMap['worker_healthcheck_interval'] || '30')
    settings.value.worker_auto_restart = settingsMap['worker_auto_restart'] === 'true'
    settings.value.whisper_model = settingsMap['whisper_model'] || 'large-v3'
    settings.value.cpu_compute_type = settingsMap['cpu_compute_type'] || settingsMap['compute_type'] || 'auto'
    settings.value.gpu_compute_type = settingsMap['gpu_compute_type'] || settingsMap['compute_type'] || 'auto'
    settings.value.skip_if_exists = settingsMap['skip_if_exists'] !== 'false'
    settings.value.scanner_enabled = settingsMap['scanner_enabled'] === 'true'
    settings.value.scanner_cron = settingsMap['scanner_cron'] || '0 2 * * *'
    settings.value.watcher_enabled = settingsMap['watcher_enabled'] === 'true'
    settings.value.bazarr_provider_enabled = settingsMap['bazarr_provider_enabled'] === 'true'

    // Parse library paths
    const pathsStr = settingsMap['library_paths'] || ''
    libraryPaths.value = pathsStr ? pathsStr.split(',').map((p: string) => p.trim()).filter((p: string) => p) : []

    // Get Bazarr API key if exists
    bazarrApiKey.value = settingsMap['bazarr_api_key'] || ''

    // Load scanner interval
    const interval = parseInt(settingsMap['scanner_schedule_interval_minutes'] || '360')
    const presets = [15, 30, 60, 120, 180, 360, 720, 1440]
    if (presets.includes(interval)) {
      scanInterval.value = interval
    } else {
      scanInterval.value = 'custom'
      customScanInterval.value = interval
    }

  } catch (error) {
    console.error('Failed to load settings:', error)
    alert('Failed to load settings')
  } finally {
    loading.value = false
  }
}

async function saveSettings() {
  saving.value = true

  try {
    // Calculate final scan interval
    const finalScanInterval = scanInterval.value === 'custom' ? customScanInterval.value : scanInterval.value

    // Force GPU worker count to 0 if no GPU detected
    const gpuWorkerCount = hasGPU.value ? settings.value.worker_gpu_count : 0

    const updates: Record<string, string> = {
      operation_mode: settings.value.operation_mode,
      log_level: settings.value.log_level,
      worker_cpu_count: settings.value.worker_cpu_count.toString(),
      worker_gpu_count: gpuWorkerCount.toString(),
      worker_healthcheck_interval: settings.value.worker_healthcheck_interval.toString(),
      worker_auto_restart: settings.value.worker_auto_restart.toString(),
      whisper_model: settings.value.whisper_model,
      cpu_compute_type: settings.value.cpu_compute_type,
      gpu_compute_type: settings.value.gpu_compute_type,
      skip_if_exists: settings.value.skip_if_exists.toString(),
      scanner_enabled: settings.value.scanner_enabled.toString(),
      scanner_schedule_interval_minutes: finalScanInterval.toString(),
      watcher_enabled: settings.value.watcher_enabled.toString(),
      bazarr_provider_enabled: settings.value.bazarr_provider_enabled.toString(),
      library_paths: libraryPaths.value.join(',')
    }

    await axios.post('/api/settings/bulk-update', { settings: updates })

    hasChanges.value = false
    alert('Settings saved successfully! Some changes may require a restart.')

    // Reload config
    await configStore.fetchConfig()

  } catch (error: any) {
    console.error('Failed to save settings:', error)
    alert('Failed to save settings: ' + (error.response?.data?.detail || error.message))
  } finally {
    saving.value = false
  }
}

function addPath(path: string) {
  if (path && !libraryPaths.value.includes(path)) {
    libraryPaths.value.push(path)
    markChanged()
  }
  showPathBrowser.value = false
}

function removePath(index: number) {
  libraryPaths.value.splice(index, 1)
  markChanged()
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  alert('Copied to clipboard!')
}

function handleIntervalChange() {
  markChanged()
}

function handleCustomIntervalChange() {
  markChanged()
}

function getScanIntervalText(): string {
  const interval = scanInterval.value === 'custom' ? customScanInterval.value : scanInterval.value

  if (!interval || interval <= 0) return 'Invalid interval'

  if (interval < 60) {
    return `${interval} minutes`
  } else if (interval < 1440) {
    const hours = Math.floor(interval / 60)
    const mins = interval % 60
    return mins > 0 ? `${hours}h ${mins}m` : `${hours} hours`
  } else {
    const days = Math.floor(interval / 1440)
    const hours = Math.floor((interval % 1440) / 60)
    if (hours > 0) {
      return `${days} days ${hours}h`
    }
    return `${days} days`
  }
}

onMounted(async () => {
  // Detect GPU first so we can properly handle GPU worker count
  await configStore.detectGPU()
  await loadSettings()
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

.settings-container {
  max-width: 1200px;
}

.settings-card {
  margin-bottom: var(--spacing-lg);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.setting-item.full-width {
  grid-column: 1 / -1;
}

.setting-label {
  font-weight: 600;
  color: var(--text-primary);
  font-size: 0.875rem;
}

.setting-description {
  display: block;
  font-weight: 400;
  color: var(--text-secondary);
  font-size: 0.75rem;
  margin-top: var(--spacing-xs);
}

.setting-input {
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.875rem;
}

.setting-input:focus {
  outline: none;
  border-color: var(--accent-color);
}

.setting-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--secondary-bg);
}

.warning-message {
  color: var(--warning-color);
  font-size: 0.75rem;
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-xs);
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  transition: 0.3s;
  border-radius: 26px;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: var(--text-secondary);
  transition: 0.3s;
  border-radius: 50%;
}

input:checked + .toggle-slider {
  background-color: var(--accent-color);
  border-color: var(--accent-color);
}

input:checked + .toggle-slider:before {
  transform: translateX(24px);
  background-color: white;
}

/* Paths List */
.paths-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.path-display {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.path-code {
  flex: 1;
  background: var(--primary-bg);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  color: var(--accent-color);
  font-family: monospace;
  font-size: 0.875rem;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
  padding: var(--spacing-xs);
  border-radius: var(--radius-sm);
  transition: background-color var(--transition-fast);
}

.btn-icon:hover {
  background: var(--secondary-bg);
}

.copy-field {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  background: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.copy-field code {
  flex: 1;
  color: var(--accent-color);
  font-family: monospace;
  word-break: break-all;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
}

/* Scanner Interval Configuration */
.interval-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.custom-interval-input {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding: var(--spacing-md);
  background: var(--tertiary-bg);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--accent-color);
}

.help-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-style: italic;
}

.interval-preview {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
}

.preview-icon {
  font-size: 1.5rem;
}

.preview-text {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.preview-text strong {
  color: var(--accent-color);
  font-weight: 600;
}

@media (max-width: 768px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>

