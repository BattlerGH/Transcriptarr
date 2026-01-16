<template>
  <Transition name="slide-down">
    <div v-if="!isOnline" class="connection-overlay">
      <div class="connection-banner">
        <div class="banner-icon">⚠️</div>
        <div class="banner-content">
          <h2 class="banner-title">No Connection to Backend</h2>
          <p class="banner-message">
            The backend server is not responding. Please check that the server is running and try again.
          </p>
          <p class="banner-status">
            Attempting to reconnect...
            <span class="reconnect-indicator">●</span>
          </p>
        </div>
      </div>
      <div class="overlay-backdrop"></div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useSystemStore } from '@/stores/system'

const systemStore = useSystemStore()

const isOnline = computed(() => systemStore.isOnline)
</script>

<style scoped>
.connection-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 99999;
  display: flex;
  justify-content: center;
  padding-top: var(--spacing-xl);
}

.overlay-backdrop {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  backdrop-filter: blur(4px);
  z-index: 1;
}

.connection-banner {
  position: relative;
  z-index: 2;
  max-width: 600px;
  width: calc(100% - 2 * var(--spacing-xl));
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
  border: 3px solid #ff4444;
  border-radius: var(--radius-lg);
  padding: var(--spacing-xl);
  box-shadow: 0 20px 60px rgba(255, 68, 68, 0.5);
  animation: shake 0.5s ease-in-out;
  height: fit-content;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-10px); }
  20%, 40%, 60%, 80% { transform: translateX(10px); }
}

.banner-icon {
  font-size: 4rem;
  text-align: center;
  margin-bottom: var(--spacing-md);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.1); opacity: 0.8; }
}

.banner-content {
  text-align: center;
}

.banner-title {
  font-size: 2rem;
  font-weight: 700;
  color: white;
  margin-bottom: var(--spacing-md);
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
}

.banner-message {
  font-size: 1.125rem;
  color: rgba(255, 255, 255, 0.95);
  margin-bottom: var(--spacing-lg);
  line-height: 1.6;
}

.banner-status {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
  font-weight: 500;
}

.reconnect-indicator {
  display: inline-block;
  animation: blink 1.5s infinite;
  color: white;
  font-size: 1.5rem;
}

@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

/* Transition animations */
.slide-down-enter-active {
  transition: all 0.4s ease-out;
}

.slide-down-leave-active {
  transition: all 0.3s ease-in;
}

.slide-down-enter-from {
  transform: translateY(-100%);
  opacity: 0;
}

.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}

@media (max-width: 768px) {
  .connection-banner {
    width: calc(100% - 2 * var(--spacing-md));
    padding: var(--spacing-lg);
  }

  .banner-title {
    font-size: 1.5rem;
  }

  .banner-message {
    font-size: 1rem;
  }

  .banner-icon {
    font-size: 3rem;
  }
}
</style>

