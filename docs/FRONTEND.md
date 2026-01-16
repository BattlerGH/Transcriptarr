# Transcriptarr Frontend

Technical documentation for the Vue 3 frontend application.

## Table of Contents

- [Overview](#overview)
- [Technology Stack](#technology-stack)
- [Directory Structure](#directory-structure)
- [Development Setup](#development-setup)
- [Views](#views)
- [Components](#components)
- [State Management](#state-management)
- [API Service](#api-service)
- [Routing](#routing)
- [Styling](#styling)
- [Build and Deployment](#build-and-deployment)

---

## Overview

The Transcriptarr frontend is a Single Page Application (SPA) built with Vue 3, featuring:

- **6 Complete Views**: Dashboard, Queue, Scanner, Rules, Workers, Settings
- **Real-time Updates**: Polling-based status updates
- **Dark Theme**: Tdarr-inspired dark UI
- **Type Safety**: Full TypeScript support
- **State Management**: Pinia stores for shared state

---

## Technology Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Vue.js | 3.4+ | UI Framework |
| Vue Router | 4.2+ | Client-side routing |
| Pinia | 2.1+ | State management |
| Axios | 1.6+ | HTTP client |
| TypeScript | 5.3+ | Type safety |
| Vite | 5.0+ | Build tool / dev server |

---

## Directory Structure

```
frontend/
├── public/                     # Static assets (favicon, etc.)
├── src/
│   ├── main.ts                 # Application entry point
│   ├── App.vue                 # Root component + navigation
│   │
│   ├── views/                  # Page components (routed)
│   │   ├── DashboardView.vue   # System overview + resources
│   │   ├── QueueView.vue       # Job management
│   │   ├── ScannerView.vue     # Scanner control
│   │   ├── RulesView.vue       # Scan rules CRUD
│   │   ├── WorkersView.vue     # Worker pool management
│   │   └── SettingsView.vue    # Settings management
│   │
│   ├── components/             # Reusable components
│   │   ├── ConnectionWarning.vue  # Backend connection status
│   │   ├── PathBrowser.vue        # Filesystem browser modal
│   │   └── SetupWizard.vue        # First-run setup wizard
│   │
│   ├── stores/                 # Pinia state stores
│   │   ├── config.ts           # Configuration store
│   │   ├── system.ts           # System status store
│   │   ├── workers.ts          # Workers store
│   │   └── jobs.ts             # Jobs store
│   │
│   ├── services/
│   │   └── api.ts              # Axios API client
│   │
│   ├── router/
│   │   └── index.ts            # Vue Router configuration
│   │
│   ├── types/
│   │   └── api.ts              # TypeScript interfaces
│   │
│   └── assets/
│       └── css/
│           └── main.css        # Global styles (dark theme)
│
├── index.html                  # HTML template
├── vite.config.ts              # Vite configuration
├── tsconfig.json               # TypeScript configuration
└── package.json                # Dependencies
```

---

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- Backend server running on port 8000

### Installation

```bash
cd frontend

# Install dependencies
npm install

# Start development server (with proxy to backend)
npm run dev
```

### Development URLs

| URL | Description |
|-----|-------------|
| http://localhost:3000 | Frontend dev server |
| http://localhost:8000 | Backend API |
| http://localhost:8000/docs | Swagger API docs |

### Scripts

```bash
npm run dev      # Start dev server with HMR
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

---

## Views

### DashboardView

**Path**: `/`

System overview with real-time resource monitoring.

**Features**:
- System status (running/stopped)
- CPU usage gauge
- RAM usage gauge
- GPU usage gauges (per device)
- Recent jobs list
- Worker pool summary
- Scanner status

**Data Sources**:
- `GET /api/status`
- `GET /api/system/resources`
- `GET /api/jobs?page_size=10`

### QueueView

**Path**: `/queue`

Job queue management with filtering and pagination.

**Features**:
- Job list with status icons
- Status filter (All/Queued/Processing/Completed/Failed)
- Pagination controls
- Retry failed jobs
- Cancel queued/processing jobs
- Clear completed jobs
- Job progress display
- Processing time display

**Data Sources**:
- `GET /api/jobs`
- `GET /api/jobs/stats`
- `POST /api/jobs/{id}/retry`
- `DELETE /api/jobs/{id}`
- `POST /api/jobs/queue/clear`

### ScannerView

**Path**: `/scanner`

Library scanner control and configuration.

**Features**:
- Scanner status display
- Start/stop scheduler
- Start/stop file watcher
- Manual scan trigger
- Scan results display
- Next scan time
- Total files scanned counter

**Data Sources**:
- `GET /api/scanner/status`
- `POST /api/scanner/scan`
- `POST /api/scanner/scheduler/start`
- `POST /api/scanner/scheduler/stop`
- `POST /api/scanner/watcher/start`
- `POST /api/scanner/watcher/stop`

### RulesView

**Path**: `/rules`

Scan rules CRUD management.

**Features**:
- Rules list with priority ordering
- Create new rule (modal)
- Edit existing rule (modal)
- Delete rule (with confirmation)
- Toggle rule enabled/disabled
- Condition configuration
- Action configuration

**Data Sources**:
- `GET /api/scan-rules`
- `POST /api/scan-rules`
- `PUT /api/scan-rules/{id}`
- `DELETE /api/scan-rules/{id}`
- `POST /api/scan-rules/{id}/toggle`

### WorkersView

**Path**: `/workers`

Worker pool management.

**Features**:
- Worker list with status
- Add CPU worker
- Add GPU worker (with device selection)
- Remove worker
- Start/stop pool
- Worker statistics
- Current job display per worker
- Progress and ETA display

**Data Sources**:
- `GET /api/workers`
- `GET /api/workers/stats`
- `POST /api/workers`
- `DELETE /api/workers/{id}`
- `POST /api/workers/pool/start`
- `POST /api/workers/pool/stop`

### SettingsView

**Path**: `/settings`

Database-backed settings management.

**Features**:
- Settings grouped by category
- Category tabs (General, Workers, Transcription, Scanner, Bazarr)
- Edit settings in-place
- Save changes button
- Change detection (unsaved changes warning)
- Setting descriptions

**Data Sources**:
- `GET /api/settings`
- `PUT /api/settings/{key}`
- `POST /api/settings/bulk-update`

---

## Components

### ConnectionWarning

Displays warning banner when backend is unreachable.

**Props**: None

**State**: Uses `systemStore.isConnected`

### PathBrowser

Modal component for browsing filesystem paths.

**Props**:
- `show: boolean` - Show/hide modal
- `initialPath: string` - Starting path

**Emits**:
- `select(path: string)` - Path selected
- `close()` - Modal closed

**API Calls**:
- `GET /api/filesystem/browse?path={path}`
- `GET /api/filesystem/common-paths`

### SetupWizard

First-run setup wizard component.

**Props**: None

**Features**:
- Mode selection (Standalone/Bazarr)
- Library path configuration
- Scan rule creation
- Worker configuration
- Scanner interval setting

**API Calls**:
- `GET /api/setup/status`
- `POST /api/setup/standalone`
- `POST /api/setup/bazarr-slave`
- `POST /api/setup/skip`

---

## State Management

### Pinia Stores

#### systemStore (`stores/system.ts`)

Global system state.

```typescript
interface SystemState {
  isConnected: boolean
  status: SystemStatus | null
  resources: SystemResources | null
  loading: boolean
  error: string | null
}

// Actions
fetchStatus()      // Fetch /api/status
fetchResources()   // Fetch /api/system/resources
startPolling()     // Start auto-refresh
stopPolling()      // Stop auto-refresh
```

#### workersStore (`stores/workers.ts`)

Worker pool state.

```typescript
interface WorkersState {
  workers: Worker[]
  stats: WorkerStats | null
  loading: boolean
  error: string | null
}

// Actions
fetchWorkers()                      // Fetch all workers
fetchStats()                        // Fetch pool stats
addWorker(type, deviceId?)          // Add worker
removeWorker(id)                    // Remove worker
startPool(cpuCount, gpuCount)       // Start pool
stopPool()                          // Stop pool
```

#### jobsStore (`stores/jobs.ts`)

Job queue state.

```typescript
interface JobsState {
  jobs: Job[]
  stats: QueueStats | null
  total: number
  page: number
  pageSize: number
  statusFilter: string | null
  loading: boolean
  error: string | null
}

// Actions
fetchJobs()                 // Fetch with current filters
fetchStats()                // Fetch queue stats
retryJob(id)                // Retry failed job
cancelJob(id)               // Cancel job
clearCompleted()            // Clear completed jobs
setStatusFilter(status)     // Update filter
setPage(page)               // Change page
```

#### configStore (`stores/config.ts`)

Settings configuration state.

```typescript
interface ConfigState {
  settings: Setting[]
  loading: boolean
  error: string | null
  pendingChanges: Record<string, string>
}

// Actions
fetchSettings(category?)    // Fetch settings
updateSetting(key, value)   // Queue update
saveChanges()               // Save all pending
discardChanges()            // Discard pending
```

---

## API Service

### Configuration (`services/api.ts`)

```typescript
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default api
```

### Usage Example

```typescript
import api from '@/services/api'

// GET request
const response = await api.get('/jobs', {
  params: { status_filter: 'queued', page: 1 }
})

// POST request
const job = await api.post('/jobs', {
  file_path: '/media/video.mkv',
  target_lang: 'spa'
})

// PUT request
await api.put('/settings/worker_cpu_count', {
  value: '2'
})

// DELETE request
await api.delete(`/jobs/${jobId}`)
```

---

## Routing

### Route Configuration

```typescript
const routes = [
  { path: '/', name: 'Dashboard', component: DashboardView },
  { path: '/workers', name: 'Workers', component: WorkersView },
  { path: '/queue', name: 'Queue', component: QueueView },
  { path: '/scanner', name: 'Scanner', component: ScannerView },
  { path: '/rules', name: 'Rules', component: RulesView },
  { path: '/settings', name: 'Settings', component: SettingsView }
]
```

### Navigation

Navigation is handled in `App.vue` with a sidebar menu.

```vue
<nav class="sidebar">
  <router-link to="/">Dashboard</router-link>
  <router-link to="/workers">Workers</router-link>
  <router-link to="/queue">Queue</router-link>
  <router-link to="/scanner">Scanner</router-link>
  <router-link to="/rules">Rules</router-link>
  <router-link to="/settings">Settings</router-link>
</nav>

<main class="content">
  <router-view />
</main>
```

---

## Styling

### Dark Theme

The application uses a Tdarr-inspired dark theme defined in `assets/css/main.css`.

**Color Palette**:

| Variable | Value | Usage |
|----------|-------|-------|
| --bg-primary | #1a1a2e | Main background |
| --bg-secondary | #16213e | Card background |
| --bg-tertiary | #0f3460 | Hover states |
| --text-primary | #eaeaea | Primary text |
| --text-secondary | #a0a0a0 | Secondary text |
| --accent-primary | #e94560 | Buttons, links |
| --accent-success | #4ade80 | Success states |
| --accent-warning | #fbbf24 | Warning states |
| --accent-error | #ef4444 | Error states |

### Component Styling

Components use scoped CSS with CSS variables:

```vue
<style scoped>
.card {
  background: var(--bg-secondary);
  border-radius: 8px;
  padding: 1.5rem;
}

.btn-primary {
  background: var(--accent-primary);
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-primary:hover {
  opacity: 0.9;
}
</style>
```

---

## Build and Deployment

### Production Build

```bash
cd frontend
npm run build
```

This creates a `dist/` folder with:
- `index.html` - Entry HTML
- `assets/` - JS, CSS bundles (hashed filenames)

### Deployment Options

#### Option 1: Served by Backend (Recommended)

The FastAPI backend automatically serves the frontend from `frontend/dist/`:

```python
# backend/app.py
frontend_path = Path(__file__).parent.parent / "frontend" / "dist"

if frontend_path.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_path / "assets")))

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str = ""):
        return FileResponse(str(frontend_path / "index.html"))
```

**Access**: http://localhost:8000

#### Option 2: Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name transcriptorio.local;

    # Frontend
    location / {
        root /var/www/transcriptorio/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

#### Option 3: Docker

```dockerfile
# Build frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Final image
FROM python:3.12-slim
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist
# ... rest of backend setup
```

---

## TypeScript Interfaces

### Key Types (`types/api.ts`)

```typescript
// Job
interface Job {
  id: string
  file_path: string
  file_name: string
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'
  priority: number
  progress: number
  // ... more fields
}

// Worker
interface Worker {
  worker_id: string
  worker_type: 'cpu' | 'gpu'
  device_id: number | null
  status: 'idle' | 'busy' | 'stopped' | 'error'
  current_job_id: string | null
  jobs_completed: number
  jobs_failed: number
}

// Setting
interface Setting {
  id: number
  key: string
  value: string | null
  description: string | null
  category: string | null
  value_type: string | null
}

// ScanRule
interface ScanRule {
  id: number
  name: string
  enabled: boolean
  priority: number
  conditions: ScanRuleConditions
  action: ScanRuleAction
}
```
