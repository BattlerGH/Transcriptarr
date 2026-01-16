<template>
  <div class="setup-wizard-overlay">
    <div class="wizard-container">
      <div class="wizard-header">
        <h1>🎬 Welcome to Transcriptarr</h1>
        <p>Let's get you set up in just a few steps</p>
      </div>

      <!-- Step 1: Choose Mode -->
      <div v-if="currentStep === 1" class="wizard-step">
        <h2>Choose Operation Mode</h2>
        <p class="step-description">How would you like to use Transcriptarr?</p>

        <div class="mode-cards">
          <div
            class="mode-card"
            :class="{ selected: selectedMode === 'standalone' }"
            @click="selectedMode = 'standalone'"
          >
            <div class="mode-icon">🏠</div>
            <h3>Standalone Mode</h3>
            <p>Automatically scan your media libraries and generate subtitles</p>
            <ul class="mode-features">
              <li>✅ Automatic library scanning</li>
              <li>✅ Customizable rules</li>
              <li>✅ Scheduled processing</li>
            </ul>
          </div>

          <div
            class="mode-card"
            :class="{ selected: selectedMode === 'bazarr_slave' }"
            @click="selectedMode = 'bazarr_slave'"
          >
            <div class="mode-icon">🔌</div>
            <h3>Bazarr Provider Mode</h3>
            <p>Integrate as a subtitle provider for Bazarr</p>
            <ul class="mode-features">
              <li>✅ Bazarr integration</li>
              <li>✅ On-demand transcription</li>
              <li>✅ Webhook support</li>
            </ul>
          </div>
        </div>

        <div class="wizard-actions">
          <button @click="skipSetup" class="btn btn-secondary">Skip Setup</button>
          <button @click="nextStep" class="btn btn-primary" :disabled="!selectedMode">
            Next →
          </button>
        </div>
      </div>

      <!-- Step 2a: Standalone Configuration -->
      <div v-if="currentStep === 2 && selectedMode === 'standalone'" class="wizard-step">
        <h2>Configure Library Paths</h2>
        <p class="step-description">Add the folders where your media files are located</p>

        <div class="paths-section">
          <div v-for="(path, index) in libraryPaths" :key="index" class="path-display">
            <code class="path-code">{{ path }}</code>
            <button @click="removePath(index)" class="btn-remove" v-if="libraryPaths.length > 1">
              🗑️
            </button>
          </div>
          <button @click="showPathBrowser = true" class="btn btn-secondary btn-sm">
            📁 Browse for Path
          </button>
        </div>

        <!-- Path Browser Modal -->
        <div v-if="showPathBrowser" class="modal-overlay" @click.self="showPathBrowser = false">
          <PathBrowser @select="addPath" @close="showPathBrowser = false" />
        </div>

        <div class="wizard-actions">
          <button @click="prevStep" class="btn btn-secondary">← Back</button>
          <button @click="nextStep" class="btn btn-primary" :disabled="!hasValidPaths">
            Next →
          </button>
        </div>
      </div>

      <!-- Step 3: Worker & Scanner Configuration (Standalone) -->
      <div v-if="currentStep === 3 && selectedMode === 'standalone'" class="wizard-step">
        <h2>⚙️ Worker & Scanner Configuration</h2>
        <p class="step-description">Configure automatic workers and scanning schedule</p>

        <div class="config-sections">
          <!-- Worker Configuration -->
          <div class="config-section">
            <h3 class="section-title">🤖 Automatic Workers</h3>
            <p class="section-description">Workers process transcription jobs. More workers = faster processing</p>

            <div class="worker-config">
              <div class="form-group">
                <label class="config-label">Number of Workers to Start:</label>
                <div class="worker-selector">
                  <button
                    @click="decrementWorkers"
                    class="btn-counter"
                    :disabled="workerCount <= 0"
                  >−</button>
                  <span class="worker-count">{{ workerCount }}</span>
                  <button
                    @click="incrementWorkers"
                    class="btn-counter"
                    :disabled="workerCount >= maxWorkers"
                  >+</button>
                </div>
                <span class="help-text">{{ getWorkerHelpText() }}</span>
              </div>

              <div v-if="workerCount > 0" class="form-group">
                <label class="config-label">Worker Type:</label>
                <div class="worker-type-selector">
                  <label class="radio-option" :class="{ disabled: !hasGpu }">
                    <input
                      type="radio"
                      v-model="workerType"
                      value="gpu"
                      :disabled="!hasGpu"
                    />
                    <span class="radio-label">
                      <span class="radio-icon">🚀</span>
                      <span class="radio-text">
                        <strong>GPU</strong>
                        <small>Faster processing (CUDA/ROCm required)</small>
                      </span>
                    </span>
                  </label>
                  <label class="radio-option">
                    <input type="radio" v-model="workerType" value="cpu" />
                    <span class="radio-label">
                      <span class="radio-icon">🖥️</span>
                      <span class="radio-text">
                        <strong>CPU</strong>
                        <small>Compatible with all systems</small>
                      </span>
                    </span>
                  </label>
                </div>
                <div v-if="!hasGpu" class="warning-box">
                  ⚠️ No GPU detected. CPU mode will be used.
                </div>
              </div>
            </div>
          </div>

          <!-- Scanner Configuration -->
          <div class="config-section">
            <h3 class="section-title">⏰ Automatic Scanning</h3>
            <p class="section-description">How often should Transcriptarr scan your libraries for new content?</p>

            <div class="scanner-config">
              <div class="form-group">
                <label class="config-label">Scan Interval:</label>
                <select v-model="scanInterval" class="form-control">
                  <option :value="15">Every 15 minutes</option>
                  <option :value="30">Every 30 minutes</option>
                  <option :value="60">Every hour</option>
                  <option :value="120">Every 2 hours</option>
                  <option :value="180">Every 3 hours</option>
                  <option :value="360">Every 6 hours (recommended)</option>
                  <option :value="720">Every 12 hours</option>
                  <option :value="1440">Daily</option>
                  <option value="custom">Custom...</option>
                </select>
              </div>

              <div v-if="scanInterval === 'custom'" class="form-group">
                <label class="config-label">Custom Interval (minutes):</label>
                <input
                  v-model.number="customScanInterval"
                  type="number"
                  min="1"
                  max="10080"
                  class="form-control"
                  placeholder="e.g., 90"
                />
                <span class="help-text">Between 1 minute and 7 days</span>
              </div>

              <div class="interval-preview">
                <span class="preview-icon">📅</span>
                <span class="preview-text">
                  Next scan will run approximately: <strong>{{ getScanIntervalText() }}</strong>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="wizard-actions">
          <button @click="prevStep" class="btn btn-secondary">← Back</button>
          <button @click="nextStep" class="btn btn-primary">
            Next →
          </button>
        </div>
      </div>

      <!-- Step 4: Standalone Rules (was Step 3) -->
      <div v-if="currentStep === 4 && selectedMode === 'standalone'" class="wizard-step">
        <h2>Configure Scan Rules</h2>
        <p class="step-description">Define rules for automatic subtitle generation</p>

        <div class="rules-section">
          <div v-for="(rule, index) in scanRules" :key="index" class="rule-card">
            <div class="rule-header">
              <h4>Rule {{ index + 1 }}</h4>
              <button @click="removeRule(index)" class="btn-remove" v-if="scanRules.length > 1">
                🗑️
              </button>
            </div>

            <div class="form-grid">
              <div class="form-group">
                <label>Rule Name</label>
                <input v-model="rule.name" type="text" class="form-control" placeholder="My Rule"/>
              </div>

              <div class="form-group">
                <label>Action</label>
                <select v-model="rule.action_type" class="form-control" @change="handleActionChange(rule)">
                  <option value="transcribe">Transcribe to English</option>
                  <option value="translate">Translate to another language</option>
                </select>
                <small class="form-hint">
                  <span v-if="rule.action_type === 'transcribe'">
                    ℹ️ Transcribes audio to English subtitles (best quality with Whisper)
                  </span>
                  <span v-else>
                    ℹ️ Transcribes to English, then translates to your target language
                  </span>
                </small>
              </div>

              <div class="form-group">
                <label>Audio Language (Source)</label>
                <select v-model="rule.audio_language_is" class="form-control" @change="handleActionChange(rule)">
                  <option value="">Any</option>
                  <option value="ja">Japanese</option>
                  <option value="en">English</option>
                  <option value="ko">Korean</option>
                  <option value="zh">Chinese</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="es">Spanish</option>
                  <option value="pt">Portuguese</option>
                </select>
              </div>

              <div v-if="rule.action_type === 'transcribe'" class="form-group">
                <label>Target Language</label>
                <input
                  type="text"
                  class="form-control"
                  value="English"
                  disabled
                />
                <small class="form-hint">
                  ℹ️ Whisper works best transcribing to English
                </small>
              </div>

              <div v-else class="form-group">
                <label>Target Language</label>
                <select v-model="rule.target_language" class="form-control">
                  <option value="es">Spanish</option>
                  <option value="en">English</option>
                  <option value="fr">French</option>
                  <option value="de">German</option>
                  <option value="pt">Portuguese</option>
                  <option value="ja">Japanese</option>
                  <option value="ko">Korean</option>
                  <option value="zh">Chinese</option>
                </select>
                <small class="form-hint">
                  ℹ️ English subtitles will be translated to this language
                </small>
              </div>
            </div>
          </div>

          <button @click="addRule" class="btn btn-secondary btn-sm">
            ➕ Add Rule
          </button>
        </div>

        <div class="wizard-actions">
          <button @click="prevStep" class="btn btn-secondary">← Back</button>
          <button @click="completeStandaloneSetup" class="btn btn-success" :disabled="submitting">
            {{ submitting ? 'Setting up...' : 'Complete Setup ✓' }}
          </button>
        </div>
      </div>

      <!-- Step 2b: Bazarr Slave Configuration -->
      <div v-if="currentStep === 2 && selectedMode === 'bazarr_slave'" class="wizard-step">
        <h2>Bazarr Provider Configuration</h2>
        <p class="step-description">Use these details to add Transcriptarr as a provider in Bazarr</p>

        <div v-if="bazarrInfo" class="bazarr-info-card">
          <div class="info-section">
            <h3>Provider URL</h3>
            <div class="copy-field">
              <code>{{ bazarrInfo.provider_url }}</code>
              <button @click="copyToClipboard(bazarrInfo.provider_url)" class="btn-copy">📋</button>
            </div>
          </div>

          <div class="info-section">
            <h3>API Key</h3>
            <div class="copy-field">
              <code>{{ bazarrInfo.api_key }}</code>
              <button @click="copyToClipboard(bazarrInfo.api_key)" class="btn-copy">📋</button>
            </div>
          </div>

          <div class="info-section">
            <h3>Provider Type</h3>
            <code>Transcriptarr (Whisper AI)</code>
          </div>

          <div class="info-instructions">
            <h4>📝 How to add in Bazarr:</h4>
            <ol>
              <li>Go to Bazarr → Settings → Providers</li>
              <li>Click "Add Provider"</li>
              <li>Select "Custom" or "Whisper"</li>
              <li>Paste the Provider URL and API Key above</li>
              <li>Save and test the connection</li>
            </ol>
          </div>
        </div>

        <div class="wizard-actions">
          <button @click="prevStep" class="btn btn-secondary">← Back</button>
          <button @click="completeBazarrSetup" class="btn btn-success" :disabled="submitting">
            {{ submitting ? 'Setting up...' : 'Complete Setup ✓' }}
          </button>
        </div>
      </div>

      <!-- Completion Step -->
      <div v-if="currentStep === 5" class="wizard-step completion">
        <div class="completion-icon">✅</div>
        <h2>Setup Complete!</h2>
        <p>Transcriptarr is ready to use</p>
        <button @click="finishSetup" class="btn btn-primary btn-lg">
          Go to Dashboard →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import PathBrowser from './PathBrowser.vue'

const emit = defineEmits(['complete'])

const currentStep = ref(1)
const selectedMode = ref<'standalone' | 'bazarr_slave' | null>(null)
const submitting = ref(false)
const showPathBrowser = ref(false)

// Standalone mode data
const libraryPaths = ref<string[]>([])
const scanRules = ref([
  {
    name: 'Default Rule',
    audio_language_is: '',
    target_language: 'es',
    action_type: 'transcribe',
    missing_external_subtitle_lang: 'es'
  }
])

// Worker configuration
const workerCount = ref(1)
const workerType = ref<'cpu' | 'gpu'>('cpu')
const hasGpu = ref(false)
const maxWorkers = ref(4)

// Scanner configuration
const scanInterval = ref<number | 'custom'>(360) // Default: 6 hours
const customScanInterval = ref(90)

// Bazarr mode data
const bazarrInfo = ref<any>(null)

const hasValidPaths = computed(() => {
  return libraryPaths.value.length > 0 && libraryPaths.value.some(path => path.trim().length > 0)
})

function nextStep() {
  if (currentStep.value === 1 && selectedMode.value === 'bazarr_slave') {
    // Bazarr mode skips to step 2 for configuration
    currentStep.value = 2
  } else {
    currentStep.value++
  }
}

function prevStep() {
  currentStep.value--
}

function addPath(path: string) {
  if (path && !libraryPaths.value.includes(path)) {
    libraryPaths.value.push(path)
  }
  showPathBrowser.value = false
}

function removePath(index: number) {
  libraryPaths.value.splice(index, 1)
}

function addRule() {
  scanRules.value.push({
    name: `Rule ${scanRules.value.length + 1}`,
    audio_language_is: '',
    target_language: 'es',
    action_type: 'transcribe',
    missing_external_subtitle_lang: 'es'
  })
}

function removeRule(index: number) {
  scanRules.value.splice(index, 1)
}

function handleActionChange(rule: any) {
  if (rule.action_type === 'transcribe') {
    // For transcribe, target language is always English (ISO 639-1)
    rule.target_language = 'en'
  }
}

// Worker configuration functions
function incrementWorkers() {
  if (workerCount.value < maxWorkers.value) {
    workerCount.value++
  }
}

function decrementWorkers() {
  if (workerCount.value > 0) {
    workerCount.value--
  }
}

function getWorkerHelpText(): string {
  if (workerCount.value === 0) {
    return 'No workers will start automatically. You can add them later.'
  } else if (workerCount.value === 1) {
    return '1 worker will start automatically on server launch'
  } else {
    return `${workerCount.value} workers will start automatically on server launch`
  }
}

// Scanner configuration functions
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

// Check GPU availability on mount
async function checkGpuAvailability() {
  try {
    const response = await axios.get('/api/system/gpu-info')
    hasGpu.value = response.data.has_gpu || false
    if (!hasGpu.value) {
      workerType.value = 'cpu'
    }
  } catch (error) {
    console.error('Failed to check GPU:', error)
    hasGpu.value = false
    workerType.value = 'cpu'
  }
}

async function completeStandaloneSetup() {
  submitting.value = true
  try {
    const validPaths = libraryPaths.value.filter(p => p.trim().length > 0)
    const finalScanInterval = scanInterval.value === 'custom' ? customScanInterval.value : scanInterval.value

    await axios.post('/api/setup/standalone', {
      library_paths: validPaths,
      scan_rules: scanRules.value,
      worker_config: {
        count: workerCount.value,
        type: workerType.value
      },
      scanner_config: {
        interval_minutes: finalScanInterval
      }
    })

    // Start configured workers automatically
    if (workerCount.value > 0) {
      for (let i = 0; i < workerCount.value; i++) {
        try {
          await axios.post('/api/workers/', {
            worker_type: workerType.value,
            device_id: workerType.value === 'gpu' ? i : null
          })
        } catch (error) {
          console.error(`Failed to start worker ${i + 1}:`, error)
        }
      }
    }

    // Start the scheduler automatically
    try {
      await axios.post('/api/scanner/scheduler/start')
    } catch (error) {
      console.error('Failed to start scheduler:', error)
    }

    // Trigger initial manual scan
    try {
      await axios.post('/api/scanner/scan', {
        paths: validPaths
      })
    } catch (error) {
      console.error('Failed to trigger initial scan:', error)
    }

    currentStep.value = 5
  } catch (error: any) {
    alert('Setup failed: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

async function completeBazarrSetup() {
  submitting.value = true
  try {
    const response = await axios.post('/api/setup/bazarr-slave', {})
    bazarrInfo.value = response.data.bazarr_info

    if (!bazarrInfo.value) {
      // If we already called setup, just show completion
      currentStep.value = 5
    }
  } catch (error: any) {
    alert('Setup failed: ' + (error.response?.data?.detail || error.message))
  } finally {
    submitting.value = false
  }
}

async function skipSetup() {
  if (confirm('Are you sure you want to skip the setup wizard?')) {
    try {
      await axios.post('/api/setup/skip')
      emit('complete')
    } catch (error) {
      console.error('Failed to skip setup:', error)
    }
  }
}

function finishSetup() {
  emit('complete')
}

function copyToClipboard(text: string) {
  navigator.clipboard.writeText(text)
  alert('Copied to clipboard!')
}

// Initialize on component mount
onMounted(() => {
  checkGpuAvailability()
})
</script>

<style scoped>
.setup-wizard-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.95);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  padding: var(--spacing-lg);
}

.wizard-container {
  background: var(--secondary-bg);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-lg);
  max-width: 800px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  padding: var(--spacing-xl);
}

.wizard-header {
  text-align: center;
  margin-bottom: var(--spacing-xl);
}

.wizard-header h1 {
  font-size: 2rem;
  margin-bottom: var(--spacing-sm);
  color: var(--accent-color);
}

.wizard-header p {
  color: var(--text-secondary);
  font-size: 1.125rem;
}

.wizard-step h2 {
  font-size: 1.5rem;
  margin-bottom: var(--spacing-sm);
  color: var(--text-primary);
}

.step-description {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-lg);
}

/* Mode Selection */
.mode-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.mode-card {
  background: var(--tertiary-bg);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  cursor: pointer;
  transition: all var(--transition-normal);
  text-align: center;
}

.mode-card:hover {
  border-color: var(--accent-color);
  transform: translateY(-4px);
}

.mode-card.selected {
  border-color: var(--accent-color);
  background: rgba(74, 158, 255, 0.1);
}

.mode-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-md);
}

.mode-card h3 {
  font-size: 1.25rem;
  margin-bottom: var(--spacing-sm);
  color: var(--text-primary);
}

.mode-card p {
  color: var(--text-secondary);
  margin-bottom: var(--spacing-md);
}

.mode-features {
  list-style: none;
  text-align: left;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.mode-features li {
  padding: var(--spacing-xs) 0;
}

/* Paths Section */
.paths-section {
  margin-bottom: var(--spacing-xl);
}

.path-display {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
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

.btn-remove {
  background: var(--danger-color);
  border: none;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.btn-remove:hover {
  opacity: 0.8;
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
  z-index: 10000;
}

/* Rules Section */
.rules-section {
  margin-bottom: var(--spacing-xl);
}

.rule-card {
  background: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
}

.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.rule-header h4 {
  color: var(--accent-color);
  font-size: 1.125rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
}

.form-control {
  width: 100%;
  padding: var(--spacing-sm);
  background: var(--primary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
}

.form-control:focus {
  outline: none;
  border-color: var(--accent-color);
}

.form-hint {
  display: block;
  margin-top: var(--spacing-xs);
  font-size: 0.75rem;
  color: var(--text-muted);
  font-style: italic;
}

/* Bazarr Info */
.bazarr-info-card {
  background: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
}

.info-section {
  margin-bottom: var(--spacing-lg);
}

.info-section h3 {
  font-size: 1rem;
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
}

.copy-field {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
}

.copy-field code {
  flex: 1;
  background: var(--primary-bg);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  color: var(--accent-color);
  font-family: monospace;
  word-break: break-all;
}

.btn-copy {
  background: var(--accent-color);
  border: none;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: opacity var(--transition-fast);
}

.btn-copy:hover {
  opacity: 0.8;
}

.info-instructions {
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--border-color);
}

/* Worker & Scanner Configuration Styles */
.config-sections {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
}

.config-section {
  background: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
}

.section-title {
  font-size: 1.25rem;
  color: var(--accent-color);
  margin-bottom: var(--spacing-xs);
}

.section-description {
  color: var(--text-secondary);
  font-size: 0.875rem;
  margin-bottom: var(--spacing-lg);
}

.worker-config,
.scanner-config {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.config-label {
  display: block;
  margin-bottom: var(--spacing-sm);
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 600;
}

/* Worker Counter */
.worker-selector {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xs);
}

.btn-counter {
  width: 40px;
  height: 40px;
  background: var(--accent-color);
  border: none;
  border-radius: var(--radius-sm);
  color: white;
  font-size: 1.5rem;
  font-weight: bold;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-counter:hover:not(:disabled) {
  background: rgba(74, 158, 255, 0.8);
  transform: scale(1.05);
}

.btn-counter:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.worker-count {
  font-size: 2rem;
  font-weight: bold;
  color: var(--accent-color);
  min-width: 50px;
  text-align: center;
}

.help-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-style: italic;
  display: block;
}

/* Worker Type Selector */
.worker-type-selector {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.radio-option {
  display: flex;
  align-items: center;
  padding: var(--spacing-md);
  background: var(--primary-bg);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.radio-option:hover:not(.disabled) {
  border-color: var(--accent-color);
}

.radio-option.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.radio-option input[type="radio"] {
  margin-right: var(--spacing-md);
  width: 20px;
  height: 20px;
  cursor: pointer;
}

.radio-option input[type="radio"]:disabled {
  cursor: not-allowed;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex: 1;
}

.radio-icon {
  font-size: 1.5rem;
}

.radio-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.radio-text strong {
  color: var(--text-primary);
  font-size: 1rem;
}

.radio-text small {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.warning-box {
  padding: var(--spacing-sm) var(--spacing-md);
  background: rgba(255, 149, 0, 0.1);
  border: 1px solid var(--warning-color);
  border-radius: var(--radius-sm);
  color: var(--warning-color);
  font-size: 0.875rem;
  margin-top: var(--spacing-sm);
}

/* Scanner Interval Preview */
.interval-preview {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background: var(--primary-bg);
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

/* Completion Step */
.completion {
  text-align: center;
}

.completion-icon {
  font-size: 4rem;
  margin-bottom: var(--spacing-lg);
}

.completion h2 {
  color: var(--accent-color);
  margin-bottom: var(--spacing-md);
}

.info-instructions ol {
  color: var(--text-secondary);
  padding-left: var(--spacing-lg);
}

.info-instructions li {
  padding: var(--spacing-xs) 0;
}

/* Wizard Actions */
.wizard-actions {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
}

.btn-lg {
  padding: var(--spacing-md) var(--spacing-xl);
  font-size: 1.125rem;
}

/* Completion */
.completion {
  text-align: center;
  padding: var(--spacing-xl);
}

.completion-icon {
  font-size: 4rem;
  margin-bottom: var(--spacing-lg);
}

.completion h2 {
  color: var(--success-color);
  margin-bottom: var(--spacing-md);
}

/* Responsive */
@media (max-width: 768px) {
  .wizard-container {
    padding: var(--spacing-lg);
  }

  .mode-cards {
    grid-template-columns: 1fr;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .wizard-actions {
    flex-direction: column;
  }
}
</style>

