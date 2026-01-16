# 🎬 Transcriptarr

**AI-powered subtitle transcription service with REST API and Web UI**

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.x-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Transcriptarr is an AI-powered subtitle transcription service based on [Subgen](https://github.com/McCloudS/subgen), featuring a modern FastAPI backend with 45+ REST endpoints, a Vue 3 web interface, and a distributed worker pool architecture.

---

## ✨ Features

### 🎯 Core Features
- **Whisper Transcription** - Support for faster-whisper and stable-ts
- **Translation** - Two-stage translation: Whisper to English, then Google Translate to target language
- **CPU/GPU Workers** - Scalable worker pool with CUDA support
- **Persistent Queue** - Priority-based queue manager with SQLite/PostgreSQL
- **Library Scanner** - Automatic scanning with configurable rules
- **REST API** - 45+ endpoints with FastAPI
- **Web UI** - Complete Vue 3 dashboard with 6 views
- **Setup Wizard** - Interactive first-run configuration
- **Real-time Monitoring** - File watcher, scheduled scans, and system resources

### 🔧 Technical Features
- **Multiprocessing**: Workers isolated in separate processes
- **Priority Queuing**: Queue with priorities and deduplication
- **Graceful Degradation**: Works without optional dependencies (Whisper, GPU)
- **Thread-Safe**: Row locking and context managers
- **Auto-retry**: Automatic retry of failed jobs
- **Health Monitoring**: Detailed statistics and health checks
- **Database-backed Settings**: All configuration stored in database, editable via Web UI

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
# Basic dependencies
pip install -r requirements.txt

# Transcription dependencies (optional - required for actual transcription)
pip install stable-ts faster-whisper
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install av>=10.0.0
```

### 2. First run (Setup Wizard)

```bash
# The setup wizard runs automatically on first start
python backend/cli.py server

# Or run setup wizard manually
python backend/cli.py setup
```

The setup wizard will guide you through:
- **Standalone mode**: Configure library paths, scan rules, and workers
- **Bazarr mode**: Configure as Bazarr subtitle provider (in development)

### 3. Start the server

```bash
# Development (with auto-reload)
python backend/cli.py server --reload

# Production
python backend/cli.py server --host 0.0.0.0 --port 8000 --workers 4
```

### 4. Access the application

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Web UI (Dashboard) |
| http://localhost:8000/docs | Swagger API Documentation |
| http://localhost:8000/redoc | ReDoc API Documentation |
| http://localhost:8000/health | Health Check Endpoint |

---

## 📋 CLI Commands

```bash
# Server
python backend/cli.py server [options]
  --host HOST           Host (default: 0.0.0.0)
  --port PORT           Port (default: 8000)
  --reload              Auto-reload for development
  --workers N           Number of uvicorn workers (default: 1)
  --log-level LEVEL     Log level (default: info)

# Setup wizard
python backend/cli.py setup     # Run setup wizard

# Database
python backend/cli.py db init   # Initialize database
python backend/cli.py db reset  # Reset (WARNING: deletes all data!)

# Standalone worker
python backend/cli.py worker --type cpu
python backend/cli.py worker --type gpu --device-id 0

# Manual scan
python backend/cli.py scan /path/to/media [--no-recursive]
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Server                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              REST API (45+ endpoints)            │   │
│  │  /api/workers  | /api/jobs     | /api/settings  │   │
│  │  /api/scanner  | /api/system   | /api/setup     │   │
│  └─────────────────────────────────────────────────┘   │
└──────────────────┬──────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┬──────────────────┐
    │              │              │                  │
    ▼              ▼              ▼                  ▼
┌────────┐   ┌──────────┐   ┌─────────┐      ┌──────────┐
│ Worker │   │  Queue   │   │ Scanner │      │ Database │
│  Pool  │◄──┤ Manager  │◄──┤ Engine  │      │ SQLite/  │
│ CPU/GPU│   │ Priority │   │ Rules + │      │ Postgres │
└────────┘   │  Queue   │   │ Watcher │      └──────────┘
             └──────────┘   └─────────┘
```

### Data Flow

1. **LibraryScanner** detects files (manual/scheduled/watcher)
2. **FileAnalyzer** analyzes with ffprobe (audio tracks, subtitles)
3. **Rules Engine** evaluates against configurable ScanRules
4. **QueueManager** adds job to persistent queue (with deduplication)
5. **Worker** processes with WhisperTranscriber
6. **Output**: Generates `.eng.srt` (transcription) or `.{lang}.srt` (translation)

---

## 🖥️ Web UI

The Web UI includes 6 complete views:

| View | Description |
|------|-------------|
| **Dashboard** | System overview, resource monitoring (CPU/RAM/GPU), recent jobs |
| **Queue** | Job management with filters, pagination, retry/cancel actions |
| **Scanner** | Scanner control, scheduler configuration, manual scan trigger |
| **Rules** | Scan rules CRUD with create/edit modal |
| **Workers** | Worker pool management, add/remove workers dynamically |
| **Settings** | Database-backed settings organized by category |

---

## 🎛️ Configuration

### Database-backed Settings

All configuration is stored in the database and manageable via:
- **Setup Wizard** (first run)
- **Settings page** in Web UI
- **Settings API** (`/api/settings`)

### Settings Categories

| Category | Settings |
|----------|----------|
| **General** | Operation mode, library paths, log level |
| **Workers** | CPU/GPU worker counts, auto-start, health check interval |
| **Transcription** | Whisper model, compute type, skip existing files |
| **Scanner** | Enable/disable, schedule interval, file watcher |
| **Bazarr** | Provider mode (in development) |

### Environment Variables

Only `DATABASE_URL` is required in `.env`:

```bash
# SQLite (default)
DATABASE_URL=sqlite:///./transcriptarr.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:pass@localhost/transcriptarr
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [docs/API.md](docs/API.md) | Complete REST API documentation (45+ endpoints) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Backend architecture and components |
| [docs/FRONTEND.md](docs/FRONTEND.md) | Frontend structure and components |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | Configuration system and settings |

---

## 🐳 Docker

```bash
# CPU only
docker build -t transcriptorio:cpu -f Dockerfile.cpu .

# GPU (NVIDIA CUDA)
docker build -t transcriptorio:gpu -f Dockerfile .

# Run
docker run -d \
  -p 8000:8000 \
  -v /path/to/media:/media \
  -v /path/to/data:/app/data \
  --gpus all \
  transcriptorio:gpu
```

---

## 📊 Project Status

| Component | Status | Progress |
|-----------|--------|----------|
| Core Backend | ✅ Complete | 100% |
| REST API (45+ endpoints) | ✅ Complete | 100% |
| Worker System | ✅ Complete | 100% |
| Library Scanner | ✅ Complete | 100% |
| Web UI (6 views) | ✅ Complete | 100% |
| Settings System | ✅ Complete | 100% |
| Setup Wizard | ✅ Complete | 100% |
| Bazarr Provider | ⏳ In Development | 30% |
| Testing Suite | ⏳ Pending | 0% |
| Docker | ⏳ Pending | 0% |

---

## 🤝 Contributing

Contributions are welcome!
---

## 📝 Credits

Based on [Subgen](https://github.com/McCloudS/subgen) by McCloudS.

Architecture redesigned with:
- FastAPI for REST APIs
- SQLAlchemy for persistence
- Multiprocessing for workers
- Whisper (stable-ts / faster-whisper) for transcription
- Vue 3 + Pinia for frontend

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.
