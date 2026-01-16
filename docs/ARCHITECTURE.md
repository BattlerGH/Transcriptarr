# TranscriptorIO Backend Architecture

Technical documentation of the backend architecture, components, and data flow.

## Table of Contents

- [Overview](#overview)
- [Directory Structure](#directory-structure)
- [Core Components](#core-components)
- [Data Flow](#data-flow)
- [Database Schema](#database-schema)
- [Transcription vs Translation](#transcription-vs-translation)
- [Worker Architecture](#worker-architecture)
- [Queue System](#queue-system)
- [Scanner System](#scanner-system)
- [Settings System](#settings-system)
- [Graceful Degradation](#graceful-degradation)
- [Thread Safety](#thread-safety)
- [Important Patterns](#important-patterns)

---

## Overview

TranscriptorIO is built with a modular architecture consisting of:

- **FastAPI Server**: REST API with 45+ endpoints
- **Worker Pool**: Multiprocessing-based transcription workers (CPU/GPU)
- **Queue Manager**: Persistent job queue with priority support
- **Library Scanner**: Rule-based file scanning with scheduler and watcher
- **Settings Service**: Database-backed configuration system

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

---

## Directory Structure

```
backend/
├── app.py                      # FastAPI application + lifespan
├── cli.py                      # CLI commands (server, db, worker, scan, setup)
├── config.py                   # Pydantic Settings (from .env)
├── setup_wizard.py             # Interactive first-run setup
│
├── core/
│   ├── database.py             # SQLAlchemy setup + session management
│   ├── models.py               # Job model + enums
│   ├── language_code.py        # ISO 639 language code utilities
│   ├── settings_model.py       # SystemSettings model (database-backed)
│   ├── settings_service.py     # Settings service with caching
│   ├── system_monitor.py       # CPU/RAM/GPU/VRAM monitoring
│   ├── queue_manager.py        # Persistent queue with priority
│   ├── worker.py               # Individual worker (Process)
│   └── worker_pool.py          # Worker pool orchestrator
│
├── transcription/
│   ├── __init__.py             # Exports + WHISPER_AVAILABLE flag
│   ├── transcriber.py          # WhisperTranscriber wrapper
│   ├── translator.py           # Google Translate integration
│   └── audio_utils.py          # ffmpeg/ffprobe utilities
│
├── scanning/
│   ├── __init__.py             # Exports (NO library_scanner import!)
│   ├── models.py               # ScanRule model
│   ├── file_analyzer.py        # ffprobe file analysis
│   ├── language_detector.py    # Audio language detection
│   ├── detected_languages.py   # Language mappings
│   └── library_scanner.py      # Scanner + scheduler + watcher
│
└── api/
    ├── __init__.py             # Router exports
    ├── workers.py              # Worker management endpoints
    ├── jobs.py                 # Job queue endpoints
    ├── scan_rules.py           # Scan rules CRUD
    ├── scanner.py              # Scanner control endpoints
    ├── settings.py             # Settings CRUD endpoints
    ├── system.py               # System resources endpoints
    ├── filesystem.py           # Filesystem browser endpoints
    └── setup_wizard.py         # Setup wizard endpoints
```

---

## Core Components

### 1. WorkerPool (`core/worker_pool.py`)

Orchestrates CPU/GPU workers as separate processes.

**Key Features:**
- Dynamic add/remove workers at runtime
- Health monitoring with auto-restart
- Thread-safe multiprocessing
- Each worker is an isolated Process

```python
from backend.core.worker_pool import worker_pool
from backend.core.worker import WorkerType

# Add GPU worker on device 0
worker_id = worker_pool.add_worker(WorkerType.GPU, device_id=0)

# Add CPU worker
worker_id = worker_pool.add_worker(WorkerType.CPU)

# Get pool stats
stats = worker_pool.get_pool_stats()
```

### 2. QueueManager (`core/queue_manager.py`)

Persistent SQLite/PostgreSQL queue with priority support.

**Key Features:**
- Job deduplication (no duplicate `file_path`)
- Row-level locking with `skip_locked=True`
- Priority-based ordering (higher first)
- FIFO within same priority (by `created_at`)
- Auto-retry failed jobs

```python
from backend.core.queue_manager import queue_manager
from backend.core.models import QualityPreset

job = queue_manager.add_job(
    file_path="/media/anime.mkv",
    file_name="anime.mkv",
    source_lang="jpn",
    target_lang="spa",
    quality_preset=QualityPreset.FAST,
    priority=5
)
```

### 3. LibraryScanner (`scanning/library_scanner.py`)

Rule-based file scanning system.

**Three Scan Modes:**
- **Manual**: One-time scan via API or CLI
- **Scheduled**: Periodic scanning with APScheduler
- **Real-time**: File watcher with watchdog library

```python
from backend.scanning.library_scanner import library_scanner

# Manual scan
result = library_scanner.scan_paths(["/media/anime"], recursive=True)

# Start scheduler (every 6 hours)
library_scanner.start_scheduler(interval_minutes=360)

# Start file watcher
library_scanner.start_file_watcher(paths=["/media/anime"], recursive=True)
```

### 4. WhisperTranscriber (`transcription/transcriber.py`)

Wrapper for stable-whisper and faster-whisper.

**Key Features:**
- GPU/CPU support with auto-device detection
- VRAM management and cleanup
- Graceful degradation (works without Whisper installed)

```python
from backend.transcription.transcriber import WhisperTranscriber

transcriber = WhisperTranscriber(
    model_name="large-v3",
    device="cuda",
    compute_type="float16"
)

result = transcriber.transcribe_file(
    file_path="/media/episode.mkv",
    language="jpn",
    task="translate"  # translate to English
)

result.to_srt("episode.eng.srt")
```

### 5. SettingsService (`core/settings_service.py`)

Database-backed configuration with caching.

```python
from backend.core.settings_service import settings_service

# Get setting
value = settings_service.get("worker_cpu_count", default=1)

# Set setting
settings_service.set("worker_cpu_count", "2")

# Bulk update
settings_service.bulk_update({
    "worker_cpu_count": "2",
    "scanner_enabled": "true"
})
```

---

## Data Flow

```
1. LibraryScanner detects file (manual/scheduled/watcher)
   ↓
2. FileAnalyzer analyzes with ffprobe
   - Audio tracks (codec, language, channels)
   - Embedded subtitles
   - External .srt files
   - Duration, video info
   ↓
3. Rules Engine evaluates against ScanRules (priority order)
   - Checks all conditions (audio language, missing subs, etc.)
   - First matching rule wins
   ↓
4. If match → QueueManager.add_job()
   - Deduplication check (no duplicate file_path)
   - Assigns priority based on rule
   ↓
5. Worker pulls job from queue
   - Uses with_for_update(skip_locked=True)
   - FIFO within same priority
   ↓
6. WhisperTranscriber processes with model
   - Stage 1: Audio → English (Whisper translate)
   - Stage 2: English → Target (Google Translate, if needed)
   ↓
7. Generate output SRT file(s)
   - .eng.srt (always)
   - .{target}.srt (if translate mode)
   ↓
8. Job marked completed ✓
```

---

## Database Schema

### Job Table (`jobs`)

```sql
id                      VARCHAR PRIMARY KEY
file_path               VARCHAR UNIQUE      -- Ensures no duplicates
file_name               VARCHAR
status                  VARCHAR             -- queued/processing/completed/failed/cancelled
priority                INTEGER
source_lang             VARCHAR
target_lang             VARCHAR
quality_preset          VARCHAR             -- fast/balanced/best
transcribe_or_translate VARCHAR             -- transcribe/translate
progress                FLOAT
current_stage           VARCHAR
eta_seconds             INTEGER
created_at              DATETIME
started_at              DATETIME
completed_at            DATETIME
output_path             VARCHAR
srt_content             TEXT
segments_count          INTEGER
error                   TEXT
retry_count             INTEGER
max_retries             INTEGER
worker_id               VARCHAR
vram_used_mb            INTEGER
processing_time_seconds FLOAT
```

### ScanRule Table (`scan_rules`)

```sql
id                          INTEGER PRIMARY KEY
name                        VARCHAR UNIQUE
enabled                     BOOLEAN
priority                    INTEGER         -- Higher = evaluated first

-- Conditions (all must match):
audio_language_is           VARCHAR         -- ISO 639-2
audio_language_not          VARCHAR         -- Comma-separated
audio_track_count_min       INTEGER
has_embedded_subtitle_lang  VARCHAR
missing_embedded_subtitle_lang VARCHAR
missing_external_subtitle_lang VARCHAR
file_extension              VARCHAR         -- Comma-separated

-- Action:
action_type                 VARCHAR         -- transcribe/translate
target_language             VARCHAR
quality_preset              VARCHAR
job_priority                INTEGER

created_at                  DATETIME
updated_at                  DATETIME
```

### SystemSettings Table (`system_settings`)

```sql
id          INTEGER PRIMARY KEY
key         VARCHAR UNIQUE
value       TEXT
description TEXT
category    VARCHAR             -- general/workers/transcription/scanner/bazarr
value_type  VARCHAR             -- string/integer/boolean/list
created_at  DATETIME
updated_at  DATETIME
```

---

## Transcription vs Translation

### Understanding the Two Modes

**Mode 1: `transcribe`** (Audio → English subtitles)
```
Audio (any language) → Whisper (task='translate') → English SRT
Example: Japanese audio → anime.eng.srt
```

**Mode 2: `translate`** (Audio → English → Target language)
```
Audio (any language) → Whisper (task='translate') → English SRT
                    → Google Translate → Target language SRT
Example: Japanese audio → anime.eng.srt + anime.spa.srt
```

### Why Two Stages?

**Whisper Limitation**: Whisper can only translate TO English, not between other languages.

**Solution**: Two-stage process:
1. **Stage 1 (Always)**: Whisper converts audio to English using `task='translate'`
2. **Stage 2 (Only for translate mode)**: Google Translate converts English to target language

### Output Files

| Mode | Target | Output Files |
|------|--------|--------------|
| transcribe | spa | `.eng.srt` only |
| translate | spa | `.eng.srt` + `.spa.srt` |
| translate | fra | `.eng.srt` + `.fra.srt` |

---

## Worker Architecture

### Worker Types

| Type | Description | Device |
|------|-------------|--------|
| CPU | Uses CPU for inference | None |
| GPU | Uses NVIDIA GPU | cuda:N |

### Worker Lifecycle

```
                    ┌─────────────┐
                    │   CREATED   │
                    └──────┬──────┘
                           │ start()
                           ▼
                    ┌─────────────┐
        ┌──────────│    IDLE     │◄─────────┐
        │          └──────┬──────┘          │
        │                 │ get_job()       │ job_done()
        │                 ▼                 │
        │          ┌─────────────┐          │
        │          │    BUSY     │──────────┘
        │          └──────┬──────┘
        │                 │ error
        │                 ▼
        │          ┌─────────────┐
        └──────────│    ERROR    │
                   └─────────────┘
```

### Process Isolation

Each worker runs in a separate Python process:
- Memory isolation (VRAM per GPU worker)
- Crash isolation (one worker crash doesn't affect others)
- Independent model loading

---

## Queue System

### Priority System

```python
# Priority values
BAZARR_REQUEST = base_priority + 10    # Highest (external request)
MANUAL_REQUEST = base_priority + 5     # High (user-initiated)
AUTO_SCAN      = base_priority         # Normal (scanner-generated)
```

### Job Deduplication

Jobs are deduplicated by `file_path`:
- If job exists with same `file_path`, new job is rejected
- Returns `None` from `add_job()`
- Prevents duplicate processing

### Concurrency Safety

```python
# Row-level locking prevents race conditions
job = session.query(Job).filter(
    Job.status == JobStatus.QUEUED
).with_for_update(skip_locked=True).first()
```

---

## Scanner System

### Scan Rule Evaluation

Rules are evaluated in priority order (highest first):

```python
# Pseudo-code for rule matching
for rule in rules.order_by(priority.desc()):
    if rule.enabled and matches_all_conditions(file, rule):
        create_job(file, rule.action)
        break  # First match wins
```

### Conditions

All conditions must match (AND logic):

| Condition | Match If |
|-----------|----------|
| audio_language_is | Primary audio track language equals |
| audio_language_not | Primary audio track language NOT in list |
| audio_track_count_min | Number of audio tracks >= value |
| has_embedded_subtitle_lang | Has embedded subtitle in language |
| missing_embedded_subtitle_lang | Does NOT have embedded subtitle |
| missing_external_subtitle_lang | Does NOT have external .srt file |
| file_extension | File extension in comma-separated list |

---

## Settings System

### Categories

| Category | Settings |
|----------|----------|
| general | operation_mode, library_paths, log_level |
| workers | cpu_count, gpu_count, auto_start, healthcheck_interval |
| transcription | whisper_model, compute_type, vram_management |
| scanner | enabled, schedule_interval, watcher_enabled |
| bazarr | provider_enabled, api_key |

### Caching

Settings service implements caching:
- Cache invalidated on write
- Thread-safe access
- Lazy loading from database

---

## Graceful Degradation

The system can run WITHOUT Whisper/torch/PyAV installed:

```python
# Pattern used everywhere
try:
    import stable_whisper
    WHISPER_AVAILABLE = True
except ImportError:
    stable_whisper = None
    WHISPER_AVAILABLE = False

# Later in code
if not WHISPER_AVAILABLE:
    raise RuntimeError("Install with: pip install stable-ts faster-whisper")
```

**What works without Whisper:**
- Backend server starts normally
- All APIs work fully
- Frontend development
- Scanner and rules management
- Job queue (jobs just won't be processed)

**What doesn't work:**
- Actual transcription (throws RuntimeError)

---

## Thread Safety

### Database Sessions

Always use context managers:

```python
with database.get_session() as session:
    # Session is automatically committed on success
    # Rolled back on exception
    job = session.query(Job).filter(...).first()
```

### Worker Pool

- Each worker is a separate Process (multiprocessing)
- Communication via shared memory (Manager)
- No GIL contention between workers

### Queue Manager

- Uses SQLAlchemy row locking
- `skip_locked=True` prevents deadlocks
- Transactions are short-lived

---

## Important Patterns

### Circular Import Resolution

**Critical**: `backend/scanning/__init__.py` MUST NOT import `library_scanner`:

```python
# backend/scanning/__init__.py
from backend.scanning.models import ScanRule
from backend.scanning.file_analyzer import FileAnalyzer, FileAnalysis
# DO NOT import library_scanner here!
```

**Why?**
```
library_scanner → database → models → scanning.models → database (circular!)
```

**Solution**: Import `library_scanner` locally where needed:
```python
def some_function():
    from backend.scanning.library_scanner import library_scanner
    library_scanner.scan_paths(...)
```

### Optional Imports

```python
try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    pynvml = None
    NVML_AVAILABLE = False
```

### Database Session Pattern

```python
from backend.core.database import database

with database.get_session() as session:
    # All operations within session context
    job = session.query(Job).filter(...).first()
    job.status = JobStatus.PROCESSING
    # Commit happens automatically
```

### API Response Pattern

```python
from pydantic import BaseModel

class JobResponse(BaseModel):
    id: str
    status: str
    # ...

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    with database.get_session() as session:
        job = session.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Not found")
        return JobResponse(**job.to_dict())
```
