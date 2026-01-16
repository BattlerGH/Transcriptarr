# TranscriptorIO Frontend

Vue 3 + TypeScript + Vite frontend for TranscriptorIO.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ (use nvm for easy management)
- npm or yarn

### Install nvm (if not installed)

```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Reload shell
source ~/.bashrc  # or ~/.zshrc

# Install Node.js 18
nvm install 18
nvm use 18
```

### Install Dependencies

```bash
cd frontend
npm install
```

### Development

```bash
# Start dev server (with hot-reload)
npm run dev

# Backend proxy is configured to http://localhost:8000
# Frontend runs on http://localhost:3000
```

### Build for Production

```bash
npm run build

# Output in dist/ directory
```

### Preview Production Build

```bash
npm run preview
```

## 📁 Project Structure

```
frontend/
├── src/
│   ├── assets/
│   │   └── css/
│   │       └── main.css         # Global styles (Tdarr-inspired dark theme)
│   ├── components/              # Reusable Vue components
│   ├── views/                   # Page components
│   │   ├── DashboardView.vue    # Main dashboard
│   │   ├── WorkersView.vue      # Worker management
│   │   ├── QueueView.vue        # Job queue
│   │   ├── ScannerView.vue      # Library scanner
│   │   ├── RulesView.vue        # Scan rules
│   │   └── SettingsView.vue     # Settings
│   ├── stores/                  # Pinia state management
│   │   ├── system.ts            # System status store
│   │   ├── workers.ts           # Workers store
│   │   └── jobs.ts              # Jobs store
│   ├── services/
│   │   └── api.ts               # Axios API client
│   ├── types/
│   │   └── api.ts               # TypeScript interfaces
│   ├── router/
│   │   └── index.ts             # Vue Router configuration
│   ├── App.vue                  # Root component
│   └── main.ts                  # App entry point
├── index.html
├── vite.config.ts               # Vite configuration
├── tsconfig.json                # TypeScript configuration
└── package.json
```

## 🎨 Design

### Theme
- Dark theme inspired by Tdarr
- Color palette optimized for monitoring and data visualization
- Fully responsive design

### Features Implemented
- ✅ Dashboard with system overview
- ✅ Worker management with real-time updates
- ✅ Auto-refresh every 3-5 seconds
- ✅ Modal dialogs for actions
- ✅ Status badges and progress bars
- ⏳ Job queue view (placeholder)
- ⏳ Scanner control (placeholder)
- ⏳ Rules editor (placeholder)
- ⏳ Settings (placeholder)

## 🔌 API Integration

The frontend communicates with the backend API via Axios:

```typescript
// Example usage
import { workersApi } from '@/services/api'

// Get all workers
const workers = await workersApi.getAll()

// Add a GPU worker
await workersApi.add({
  worker_type: 'gpu',
  device_id: 0
})
```

### API Proxy Configuration

Vite dev server proxies API requests to the backend:

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': 'http://localhost:8000',
    '/health': 'http://localhost:8000'
  }
}
```

## 🧩 State Management

Uses Pinia for state management:

```typescript
// Example store usage
import { useWorkersStore } from '@/stores/workers'

const workersStore = useWorkersStore()
await workersStore.fetchWorkers()
```

## 🔧 Development

### Recommended IDE Setup

- VS Code with extensions:
  - Volar (Vue 3 support)
  - TypeScript Vue Plugin
  - ESLint

### Type Checking

```bash
npm run build  # Includes type checking with vue-tsc
```

### Linting

```bash
npm run lint
```

## 📦 Dependencies

### Core
- **Vue 3** - Progressive JavaScript framework
- **Vite** - Fast build tool
- **TypeScript** - Type safety
- **Vue Router** - Client-side routing
- **Pinia** - State management
- **Axios** - HTTP client

### Dev Dependencies
- vue-tsc - Vue TypeScript compiler
- ESLint - Code linting
- TypeScript ESLint - TypeScript linting rules

## 🚀 Deployment

### Standalone Deployment

```bash
# Build
npm run build

# Serve with any static file server
npx serve dist
```

### Integration with Backend

The built frontend can be served by FastAPI:

```python
# backend/app.py
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

## 📱 Responsive Design

- Desktop-first design
- Breakpoint: 768px for mobile
- Touch-friendly controls
- Optimized for tablets and phones

## 🎯 Roadmap

### Phase 1 (Current)
- ✅ Dashboard
- ✅ Worker management
- ⏳ Job queue view

### Phase 2
- ⏳ Scanner controls
- ⏳ Rules editor
- ⏳ Settings page

### Phase 3
- ⏳ WebSocket support for real-time updates
- ⏳ Advanced filtering and search
- ⏳ Job logs viewer
- ⏳ Dark/light theme toggle

## 🐛 Known Issues

- Auto-refresh uses polling (will migrate to WebSocket)
- Some views are placeholders
- No authentication yet

## 📄 License

MIT License - Same as backend

