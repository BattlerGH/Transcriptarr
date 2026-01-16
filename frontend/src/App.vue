<template>
  <div id="app">
    <!-- Connection Warning (shows when backend is offline) -->
    <ConnectionWarning />

    <!-- Setup Wizard (first run only) -->
    <SetupWizard v-if="showSetupWizard" @complete="onSetupComplete" />

    <header class="app-header">
      <div class="container">
        <div class="header-content">
          <div class="logo">
            <h1>🎬 TranscriptorIO</h1>
            <span class="subtitle">AI-Powered Subtitle Transcription</span>
          </div>
          <nav class="main-nav">
            <router-link to="/" class="nav-link">Dashboard</router-link>
            <router-link to="/workers" class="nav-link">Workers</router-link>
            <router-link to="/queue" class="nav-link">Queue</router-link>
            <router-link v-if="configStore.isStandalone" to="/scanner" class="nav-link">Scanner</router-link>
            <router-link v-if="configStore.isStandalone" to="/rules" class="nav-link">Rules</router-link>
            <router-link to="/settings" class="nav-link">Settings</router-link>
          </nav>
          <div class="status-indicator" :class="{ 'online': systemStore.isOnline }">
            <span class="status-dot"></span>
            <span class="status-text">{{ systemStore.isOnline ? 'Online' : 'Offline' }}</span>
          </div>
        </div>
      </div>
    </header>

    <main class="app-main">
      <div class="container">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <footer class="app-footer">
      <div class="container">
        <p>&copy; 2026 TranscriptorIO | Powered by Whisper AI</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useSystemStore } from '@/stores/system'
import { useConfigStore } from '@/stores/config'
import SetupWizard from '@/components/SetupWizard.vue'
import ConnectionWarning from '@/components/ConnectionWarning.vue'
import axios from 'axios'

const systemStore = useSystemStore()
const configStore = useConfigStore()
const showSetupWizard = ref(false)

let statusInterval: number | null = null

const checkStatus = async () => {
  try {
    await systemStore.fetchStatus()
  } catch (error) {
    // Error already handled in store
  }
}

const checkSetupStatus = async () => {
  try {
    const response = await axios.get('/api/setup/status')
    if (response.data.is_first_run && !response.data.setup_completed) {
      showSetupWizard.value = true
    }
  } catch (error) {
    console.error('Failed to check setup status:', error)
  }
}

const onSetupComplete = () => {
  showSetupWizard.value = false
  // Refresh page to apply new settings
  window.location.reload()
}

onMounted(() => {
  checkSetupStatus()
  checkStatus()
  configStore.fetchConfig()
  configStore.detectGPU()
  // Check status every 10 seconds
  statusInterval = window.setInterval(checkStatus, 10000)
})

onUnmounted(() => {
  if (statusInterval) {
    clearInterval(statusInterval)
  }
})
</script>

<style>
/* Global styles in main.css */
</style>

