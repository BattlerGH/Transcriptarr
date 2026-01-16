<template>
  <div class="path-browser">
    <div class="browser-header">
      <button @click="emit('close')" class="btn-close">✕</button>
      <h3>Select Directory</h3>
    </div>

    <div class="current-path">
      <span class="path-label">Current:</span>
      <code>{{ currentPath || '/' }}</code>
    </div>

    <div class="browser-body">
      <!-- Error message -->
      <div v-if="error" class="error-message">
        ⚠️ {{ error }}
      </div>

      <!-- Parent directory button -->
      <div v-if="currentPath !== '/'" class="dir-item" @click="goUp">
        <span class="dir-icon">📁</span>
        <span class="dir-name">..</span>
      </div>

      <!-- Directory list -->
      <div
        v-for="item in directories"
        :key="item.path"
        class="dir-item"
        :class="{ 'dir-item-disabled': !item.is_readable }"
        @click="openDirectory(item)"
      >
        <span class="dir-icon">{{ item.is_readable ? '📁' : '🔒' }}</span>
        <span class="dir-name">{{ item.name }}</span>
      </div>

      <div v-if="loading" class="loading-state">
        <span class="spinner-small"></span>
        Loading...
      </div>

      <div v-if="!loading && !error && directories.length === 0" class="empty-dirs">
        No subdirectories found
      </div>
    </div>

    <div class="browser-footer">
      <button @click="emit('close')" class="btn btn-secondary">Cancel</button>
      <button @click="selectPath" class="btn btn-primary">
        Select This Path
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'

const emit = defineEmits(['select', 'close'])

interface DirectoryItem {
  name: string
  path: string
  is_directory: boolean
  is_readable: boolean
}

const currentPath = ref('/')
const directories = ref<DirectoryItem[]>([])
const loading = ref(false)
const error = ref<string | null>(null)

async function loadDirectories(path: string) {
  loading.value = true
  error.value = null
  try {
    const response = await axios.get('/api/filesystem/browse', {
      params: { path }
    })

    currentPath.value = response.data.current_path
    directories.value = response.data.items.filter((item: DirectoryItem) => item.is_readable)
  } catch (err: any) {
    console.error('Failed to load directories:', err)
    error.value = err.response?.data?.detail || 'Failed to load directories'
    directories.value = []
  } finally {
    loading.value = false
  }
}

async function loadCommonPaths() {
  loading.value = true
  try {
    const response = await axios.get('/api/filesystem/common-paths')
    directories.value = response.data.filter((item: DirectoryItem) => item.is_readable)
  } catch (err) {
    console.error('Failed to load common paths:', err)
    // Fallback to root
    loadDirectories('/')
  } finally {
    loading.value = false
  }
}

function openDirectory(item: DirectoryItem) {
  if (!item.is_readable) {
    error.value = 'Permission denied'
    return
  }
  loadDirectories(item.path)
}

function goUp() {
  const parts = currentPath.value.split('/').filter(p => p)
  parts.pop()
  const parentPath = parts.length === 0 ? '/' : '/' + parts.join('/')
  loadDirectories(parentPath)
}

function selectPath() {
  emit('select', currentPath.value)
  emit('close')
}

onMounted(() => {
  // Start with common paths
  loadCommonPaths()
})
</script>

<style scoped>
.path-browser {
  background: var(--tertiary-bg);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  max-width: 600px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
}

.browser-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-bottom: 1px solid var(--border-color);
}

.browser-header h3 {
  flex: 1;
  margin: 0;
  font-size: 1.125rem;
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
  background-color: var(--secondary-bg);
  color: var(--text-primary);
}

.current-path {
  padding: var(--spacing-md);
  background: var(--secondary-bg);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.path-label {
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 600;
}

.current-path code {
  flex: 1;
  background: var(--primary-bg);
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-sm);
  color: var(--accent-color);
  font-family: monospace;
  font-size: 0.875rem;
}

.browser-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-sm);
  min-height: 300px;
  max-height: 400px;
}

.dir-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background-color var(--transition-fast);
  margin-bottom: var(--spacing-xs);
}

.dir-item:hover {
  background-color: var(--secondary-bg);
}

.dir-item-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dir-item-disabled:hover {
  background-color: transparent;
}

.error-message {
  background-color: rgba(255, 68, 68, 0.1);
  border: 1px solid rgba(255, 68, 68, 0.3);
  border-radius: var(--radius-sm);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  color: #ff6b6b;
  font-size: 0.875rem;
}

.dir-icon {
  font-size: 1.25rem;
}

.dir-name {
  color: var(--text-primary);
  font-weight: 500;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xl);
  color: var(--text-secondary);
}

.spinner-small {
  border: 2px solid var(--tertiary-bg);
  border-top: 2px solid var(--accent-color);
  border-radius: 50%;
  width: 16px;
  height: 16px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.empty-dirs {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--text-muted);
}

.browser-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-top: 1px solid var(--border-color);
}
</style>

