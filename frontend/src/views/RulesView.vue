<template>
  <div class="rules-view">
    <div class="page-header">
      <h1 class="page-title">Scan Rules</h1>
      <button @click="showCreateModal = true" class="btn btn-primary">Create Rule</button>
    </div>

    <div v-if="loading" class="spinner"></div>

    <div v-else-if="rules.length === 0" class="empty-state">
      <p>No scan rules configured yet. Create your first rule to start automatic scanning.</p>
    </div>

    <div v-else class="rules-grid">
      <div v-for="rule in rules" :key="rule.id" class="rule-card">
        <div class="rule-header">
          <h3 class="rule-name">{{ rule.name }}</h3>
          <div class="rule-actions">
            <button
              @click="toggleRule(rule)"
              :class="['btn-toggle', rule.enabled ? 'enabled' : 'disabled']"
              :title="rule.enabled ? 'Disable' : 'Enable'"
            >
              {{ rule.enabled ? '✓' : '✕' }}
            </button>
            <button @click="editRule(rule)" class="btn-edit" title="Edit">✎</button>
            <button @click="deleteRule(rule.id)" class="btn-delete" title="Delete">🗑</button>
          </div>
        </div>
        <div class="rule-body">
          <div class="rule-detail">
            <span class="detail-label">Priority:</span>
            <span class="detail-value">{{ rule.priority }}</span>
          </div>
          <div class="rule-detail">
            <span class="detail-label">Audio:</span>
            <span class="detail-value">{{ rule.conditions?.audio_language_is || 'Any' }}</span>
          </div>
          <div class="rule-detail">
            <span class="detail-label">Action:</span>
            <span class="detail-value">{{ rule.action?.action_type }} → {{ rule.action?.target_language }}</span>
          </div>
          <div v-if="rule.conditions?.missing_external_subtitle_lang" class="rule-detail">
            <span class="detail-label">Check missing:</span>
            <span class="detail-value">{{ rule.conditions.missing_external_subtitle_lang }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Rule Modal -->
    <div v-if="showCreateModal || editingRule" class="modal-overlay" @click="closeModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ editingRule ? 'Edit Rule' : 'Create Rule' }}</h2>
          <button @click="closeModal" class="btn-close">✕</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>Rule Name</label>
            <input v-model="formData.name" type="text" class="form-input" placeholder="e.g., Japanese anime to Spanish" />
          </div>
          <div class="form-group">
            <label>Priority (higher = first)</label>
            <input v-model.number="formData.priority" type="number" class="form-input" />
          </div>
          <div class="form-group">
            <label>Audio Language (empty = any)</label>
            <input v-model="formData.audio_language_is" type="text" class="form-input" placeholder="ja, en, es..." />
          </div>
          <div class="form-group">
            <label>Action Type</label>
            <select v-model="formData.action_type" class="form-select" @change="onActionTypeChange">
              <option value="transcribe">Transcribe (audio → English)</option>
              <option value="translate">Translate (audio → English → target language)</option>
            </select>
          </div>
          <div class="form-group">
            <label>
              Target Language
              <span v-if="formData.action_type === 'transcribe'" class="setting-description">
                (Fixed: en - transcribe mode only creates English subtitles)
              </span>
            </label>
            <input
              v-if="formData.action_type === 'translate'"
              v-model="formData.target_language"
              type="text"
              class="form-input"
              placeholder="es, fr, de, it..."
              required
            />
            <input
              v-else
              value="en"
              type="text"
              class="form-input"
              disabled
              readonly
            />
          </div>
          <div class="form-group">
            <label>Check Missing Subtitle</label>
            <input v-model="formData.missing_external_subtitle_lang" type="text" class="form-input" placeholder="es, en..." />
          </div>
          <div class="form-group">
            <label class="checkbox-label">
              <input v-model="formData.enabled" type="checkbox" />
              <span>Enabled</span>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="saveRule" class="btn btn-primary">{{ editingRule ? 'Update' : 'Create' }}</button>
          <button @click="closeModal" class="btn btn-secondary">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import api from '@/services/api'

interface Rule {
  id: number
  name: string
  enabled: boolean
  priority: number
  conditions: {
    audio_language_is?: string | null
    audio_language_not?: string | null
    audio_track_count_min?: number | null
    has_embedded_subtitle_lang?: string | null
    missing_embedded_subtitle_lang?: string | null
    missing_external_subtitle_lang?: string | null
    file_extension?: string | null
  }
  action: {
    action_type: string
    target_language: string
    quality_preset?: string
    job_priority?: number
  }
  created_at?: string
  updated_at?: string
}

const rules = ref<Rule[]>([])
const loading = ref(true)
const showCreateModal = ref(false)
const editingRule = ref<Rule | null>(null)

const formData = ref({
  name: '',
  priority: 10,
  audio_language_is: '',
  target_language: 'en',  // Default to 'en' for transcribe mode
  action_type: 'transcribe',
  missing_external_subtitle_lang: '',
  enabled: true
})

async function loadRules() {
  loading.value = true
  try {
    const response = await api.get('/scan-rules')
    rules.value = response.data || []
  } catch (error: any) {
    console.error('Failed to load rules:', error)
    rules.value = []
  } finally {
    loading.value = false
  }
}

async function toggleRule(rule: Rule) {
  try {
    await api.post(`/scan-rules/${rule.id}/toggle`)
    await loadRules()
  } catch (error: any) {
    alert('Failed to toggle rule: ' + (error.response?.data?.detail || error.message))
  }
}

function onActionTypeChange() {
  // When switching to transcribe mode, force target language to 'en'
  if (formData.value.action_type === 'transcribe') {
    formData.value.target_language = 'en'
  }
}

function editRule(rule: Rule) {
  editingRule.value = rule
  formData.value = {
    name: rule.name,
    priority: rule.priority,
    audio_language_is: rule.conditions?.audio_language_is || '',
    target_language: rule.action?.target_language || 'en',
    action_type: rule.action?.action_type || 'transcribe',
    missing_external_subtitle_lang: rule.conditions?.missing_external_subtitle_lang || '',
    enabled: rule.enabled
  }
}

async function saveRule() {
  try {
    // Force target_language to 'en' if action_type is 'transcribe'
    const targetLanguage = formData.value.action_type === 'transcribe'
      ? 'en'
      : formData.value.target_language

    const payload = {
      name: formData.value.name,
      enabled: formData.value.enabled,
      priority: formData.value.priority,
      conditions: {
        audio_language_is: formData.value.audio_language_is || null,
        missing_external_subtitle_lang: formData.value.missing_external_subtitle_lang || null
      },
      action: {
        action_type: formData.value.action_type,
        target_language: targetLanguage,
        quality_preset: 'fast',
        job_priority: 0
      }
    }

    if (editingRule.value) {
      await api.put(`/scan-rules/${editingRule.value.id}`, payload)
    } else {
      await api.post('/scan-rules', payload)
    }

    closeModal()
    await loadRules()
  } catch (error: any) {
    alert('Failed to save rule: ' + (error.response?.data?.detail || error.message))
  }
}

async function deleteRule(id: number) {
  if (!confirm('Delete this rule?')) return

  try {
    await api.delete(`/scan-rules/${id}`)
    await loadRules()
  } catch (error: any) {
    alert('Failed to delete rule: ' + (error.response?.data?.detail || error.message))
  }
}

function closeModal() {
  showCreateModal.value = false
  editingRule.value = null
  formData.value = {
    name: '',
    priority: 10,
    audio_language_is: '',
    target_language: 'en',  // Default to 'en' for transcribe mode
    action_type: 'transcribe',
    missing_external_subtitle_lang: '',
    enabled: true
  }
}

onMounted(() => {
  loadRules()
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

.rules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: var(--spacing-lg);
}

.rule-card {
  background-color: var(--secondary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
}

.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.rule-name {
  margin: 0;
  font-size: 1.125rem;
  color: var(--text-primary);
}

.rule-actions {
  display: flex;
  gap: var(--spacing-xs);
}

.btn-toggle, .btn-edit, .btn-delete {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  background-color: var(--tertiary-bg);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.875rem;
}

.btn-toggle.enabled {
  background-color: var(--success-color);
  color: white;
}

.btn-toggle.disabled {
  background-color: var(--text-muted);
  color: white;
}

.rule-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.rule-detail {
  display: flex;
  justify-content: space-between;
}

.detail-label {
  font-weight: 600;
  color: var(--text-secondary);
}

.detail-value {
  color: var(--text-primary);
  font-family: monospace;
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
}

.modal-body {
  padding: var(--spacing-lg);
}

.form-group {
  margin-bottom: var(--spacing-md);
}

.form-group label {
  display: block;
  margin-bottom: var(--spacing-xs);
  font-weight: 600;
  color: var(--text-secondary);
}

.form-input, .form-select {
  width: 100%;
  padding: var(--spacing-sm);
  background-color: var(--tertiary-bg);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
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
</style>
