# TranscriptorIO REST API

Complete documentation for the TranscriptorIO backend REST API.

## Table of Contents

- [Quick Start](#quick-start)
- [System Endpoints](#system-endpoints)
- [Workers API](#workers-api)
- [Jobs API](#jobs-api)
- [Scan Rules API](#scan-rules-api)
- [Scanner API](#scanner-api)
- [Settings API](#settings-api)
- [System Resources API](#system-resources-api)
- [Filesystem API](#filesystem-api)
- [Setup Wizard API](#setup-wizard-api)
- [Bazarr Provider API](#bazarr-provider-api-in-development)
- [Error Codes](#error-codes)
- [Examples](#examples)

---

## Quick Start

### Running the Server

```bash
# Using the CLI
python backend/cli.py server --host 0.0.0.0 --port 8000

# With auto-reload (development)
python backend/cli.py server --reload

# With multiple workers (production)
python backend/cli.py server --workers 4
```

### Interactive Documentation

Once the server is running:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## System Endpoints

### `GET /`

Root endpoint - API info or frontend (if built).

**Response (API mode):**
```json
{
  "name": "TranscriptorIO API",
  "version": "1.0.0",
  "status": "running",
  "message": "Frontend not built. Access API docs at /docs"
}
```

### `GET /health`

Health check for monitoring systems.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "workers": 2,
  "queue_size": 5
}
```

### `GET /api/status`

Complete system status overview.

**Response:**
```json
{
  "system": {
    "status": "running",
    "uptime_seconds": 3600.5
  },
  "workers": {
    "total_workers": 2,
    "cpu_workers": 1,
    "gpu_workers": 1,
    "idle_workers": 1,
    "busy_workers": 1,
    "total_jobs_completed": 42,
    "total_jobs_failed": 2
  },
  "queue": {
    "total_jobs": 100,
    "queued": 5,
    "processing": 2,
    "completed": 90,
    "failed": 3,
    "cancelled": 0
  },
  "scanner": {
    "scheduler_enabled": true,
    "scheduler_running": true,
    "next_scan_time": "2025-01-13T02:00:00",
    "watcher_enabled": true,
    "watcher_running": true
  }
}
```

---

## Workers API

Base path: `/api/workers`

### `GET /api/workers`

List all workers and their status.

**Response:**
```json
[
  {
    "worker_id": "worker-cpu-0",
    "worker_type": "cpu",
    "device_id": null,
    "status": "busy",
    "current_job_id": "abc123",
    "jobs_completed": 10,
    "jobs_failed": 0,
    "uptime_seconds": 3600.5,
    "current_job_progress": 45.2,
    "current_job_eta": 120
  }
]
```

### `GET /api/workers/stats`

Get worker pool statistics.

**Response:**
```json
{
  "total_workers": 2,
  "cpu_workers": 1,
  "gpu_workers": 1,
  "idle_workers": 1,
  "busy_workers": 1,
  "stopped_workers": 0,
  "error_workers": 0,
  "total_jobs_completed": 42,
  "total_jobs_failed": 2,
  "uptime_seconds": 3600.5,
  "is_running": true
}
```

### `GET /api/workers/{worker_id}`

Get specific worker status.

**Path Parameters:**
- `worker_id` (string): Worker ID

**Response:** Worker status object (same as list item)

**Errors:**
- `404`: Worker not found

### `POST /api/workers`

Add a new worker to the pool.

**Request:**
```json
{
  "worker_type": "gpu",
  "device_id": 0
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| worker_type | string | Yes | `cpu` or `gpu` |
| device_id | integer | GPU only | GPU device ID (required for GPU workers) |

**Response:** Created worker status (201)

**Errors:**
- `400`: Invalid worker type or missing device_id for GPU

### `DELETE /api/workers/{worker_id}`

Remove a worker from the pool.

**Path Parameters:**
- `worker_id` (string): Worker ID to remove

**Query Parameters:**
- `timeout` (float, default=30.0): Timeout in seconds

**Response:**
```json
{
  "message": "Worker worker-cpu-0 removed successfully"
}
```

**Errors:**
- `404`: Worker not found

### `POST /api/workers/pool/start`

Start the worker pool with specified workers.

**Query Parameters:**
- `cpu_workers` (int, default=0): Number of CPU workers
- `gpu_workers` (int, default=0): Number of GPU workers

**Response:**
```json
{
  "message": "Worker pool started: 1 CPU workers, 1 GPU workers"
}
```

### `POST /api/workers/pool/stop`

Stop all workers in the pool.

**Query Parameters:**
- `timeout` (float, default=30.0): Timeout per worker

**Response:**
```json
{
  "message": "Worker pool stopped successfully"
}
```

---

## Jobs API

Base path: `/api/jobs`

### `GET /api/jobs`

List jobs with pagination and filtering.

**Query Parameters:**
- `status_filter` (string, optional): Filter by status (`queued`, `processing`, `completed`, `failed`, `cancelled`)
- `page` (int, default=1): Page number (1-based)
- `page_size` (int, default=50, max=500): Items per page

**Response:**
```json
{
  "jobs": [
    {
      "id": "abc123",
      "file_path": "/media/anime/episode.mkv",
      "file_name": "episode.mkv",
      "job_type": "transcription",
      "status": "completed",
      "priority": 10,
      "source_lang": "jpn",
      "target_lang": "spa",
      "quality_preset": "fast",
      "transcribe_or_translate": "transcribe",
      "progress": 100.0,
      "current_stage": "finalizing",
      "eta_seconds": null,
      "created_at": "2025-01-12T10:00:00",
      "started_at": "2025-01-12T10:00:05",
      "completed_at": "2025-01-12T10:05:30",
      "output_path": "/media/anime/episode.spa.srt",
      "segments_count": 245,
      "error": null,
      "retry_count": 0,
      "worker_id": "worker-gpu-0",
      "vram_used_mb": 4096,
      "processing_time_seconds": 325.5,
      "model_used": "large-v3",
      "device_used": "cuda:0"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 50
}
```

### `GET /api/jobs/stats`

Get queue statistics.

**Response:**
```json
{
  "total_jobs": 100,
  "queued": 5,
  "processing": 2,
  "completed": 90,
  "failed": 3,
  "cancelled": 0
}
```

### `GET /api/jobs/{job_id}`

Get specific job details.

**Path Parameters:**
- `job_id` (string): Job ID

**Response:** Job object (same as list item)

**Errors:**
- `404`: Job not found

### `POST /api/jobs`

Create a new transcription job.

**Request:**
```json
{
  "file_path": "/media/anime/Attack on Titan S04E01.mkv",
  "file_name": "Attack on Titan S04E01.mkv",
  "source_lang": "jpn",
  "target_lang": "spa",
  "quality_preset": "fast",
  "transcribe_or_translate": "transcribe",
  "priority": 10,
  "is_manual_request": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| file_path | string | Yes | Full path to media file |
| file_name | string | Yes | File name |
| source_lang | string | No | Source language (ISO 639-2) |
| target_lang | string | Yes | Target subtitle language (ISO 639-2) |
| quality_preset | string | No | `fast`, `balanced`, or `best` |
| transcribe_or_translate | string | No | `transcribe` or `translate` |
| priority | int | No | Higher = processed first |
| is_manual_request | bool | No | Default: true |

**Response:** Created job (201)

**Errors:**
- `400`: Invalid quality preset
- `409`: Job already exists for this file

### `POST /api/jobs/{job_id}/retry`

Retry a failed job.

**Path Parameters:**
- `job_id` (string): Job ID to retry

**Response:** Updated job object

**Errors:**
- `404`: Job not found
- `400`: Job cannot be retried (not in failed status)

### `DELETE /api/jobs/{job_id}`

Cancel a job.

**Path Parameters:**
- `job_id` (string): Job ID to cancel

**Response:**
```json
{
  "message": "Job abc123 cancelled successfully"
}
```

**Errors:**
- `404`: Job not found
- `400`: Job already in terminal state

### `POST /api/jobs/{job_id}/cancel`

Cancel a job (POST alias for DELETE).

### `POST /api/jobs/queue/clear`

Clear all completed jobs from the queue.

**Response:**
```json
{
  "message": "Cleared 42 completed jobs"
}
```

---

## Scan Rules API

Base path: `/api/scan-rules`

### `GET /api/scan-rules`

List all scan rules.

**Query Parameters:**
- `enabled_only` (bool, default=false): Only return enabled rules

**Response:**
```json
[
  {
    "id": 1,
    "name": "Japanese anime without Spanish subs",
    "enabled": true,
    "priority": 10,
    "conditions": {
      "audio_language_is": "jpn",
      "audio_language_not": null,
      "audio_track_count_min": null,
      "has_embedded_subtitle_lang": null,
      "missing_embedded_subtitle_lang": "spa",
      "missing_external_subtitle_lang": "spa",
      "file_extension": ".mkv,.mp4"
    },
    "action": {
      "action_type": "transcribe",
      "target_language": "spa",
      "quality_preset": "fast",
      "job_priority": 5
    },
    "created_at": "2025-01-12T10:00:00",
    "updated_at": null
  }
]
```

### `GET /api/scan-rules/{rule_id}`

Get specific scan rule.

**Path Parameters:**
- `rule_id` (int): Rule ID

**Response:** Rule object (same as list item)

**Errors:**
- `404`: Rule not found

### `POST /api/scan-rules`

Create a new scan rule.

**Request:**
```json
{
  "name": "Japanese anime without Spanish subs",
  "enabled": true,
  "priority": 10,
  "conditions": {
    "audio_language_is": "jpn",
    "missing_embedded_subtitle_lang": "spa",
    "missing_external_subtitle_lang": "spa",
    "file_extension": ".mkv,.mp4"
  },
  "action": {
    "action_type": "transcribe",
    "target_language": "spa",
    "quality_preset": "fast",
    "job_priority": 5
  }
}
```

**Conditions Fields:**

| Field | Type | Description |
|-------|------|-------------|
| audio_language_is | string | Audio must be this language (ISO 639-2) |
| audio_language_not | string | Audio must NOT be (comma-separated) |
| audio_track_count_min | int | Minimum audio tracks |
| has_embedded_subtitle_lang | string | Must have embedded subtitle |
| missing_embedded_subtitle_lang | string | Must NOT have embedded subtitle |
| missing_external_subtitle_lang | string | Must NOT have external .srt |
| file_extension | string | File extensions (comma-separated) |

**Action Fields:**

| Field | Type | Description |
|-------|------|-------------|
| action_type | string | `transcribe` or `translate` |
| target_language | string | Target language (ISO 639-2) |
| quality_preset | string | `fast`, `balanced`, `best` |
| job_priority | int | Priority for created jobs |

**Response:** Created rule (201)

**Errors:**
- `409`: Rule with same name exists

### `PUT /api/scan-rules/{rule_id}`

Update a scan rule (partial update supported).

**Path Parameters:**
- `rule_id` (int): Rule ID

**Request:** Same fields as POST (all optional)

**Response:** Updated rule

**Errors:**
- `404`: Rule not found
- `409`: Name already exists

### `DELETE /api/scan-rules/{rule_id}`

Delete a scan rule.

**Path Parameters:**
- `rule_id` (int): Rule ID

**Response:**
```json
{
  "message": "Scan rule 1 deleted successfully"
}
```

**Errors:**
- `404`: Rule not found

### `POST /api/scan-rules/{rule_id}/toggle`

Toggle rule enabled/disabled.

**Path Parameters:**
- `rule_id` (int): Rule ID

**Response:** Updated rule object

**Errors:**
- `404`: Rule not found

---

## Scanner API

Base path: `/api/scanner`

### `GET /api/scanner/status`

Get scanner status.

**Response:**
```json
{
  "scheduler_enabled": true,
  "scheduler_running": true,
  "next_scan_time": "2025-01-13T02:00:00",
  "watcher_enabled": true,
  "watcher_running": true,
  "watched_paths": ["/media/anime", "/media/movies"],
  "last_scan_time": "2025-01-12T02:00:00",
  "total_scans": 1523
}
```

### `POST /api/scanner/scan`

Trigger a manual scan.

**Request (optional):**
```json
{
  "paths": ["/media/anime", "/media/movies"],
  "recursive": true
}
```

If no request body, uses `library_paths` from settings.

**Response:**
```json
{
  "scanned_files": 150,
  "matched_files": 25,
  "jobs_created": 25,
  "skipped_files": 125,
  "paths_scanned": ["/media/anime", "/media/movies"]
}
```

**Errors:**
- `400`: No library paths configured

### `POST /api/scanner/scheduler/start`

Start the scheduled scanner.

**Request (optional):**
```json
{
  "enabled": true,
  "cron_expression": "0 2 * * *",
  "paths": ["/media/anime"],
  "recursive": true
}
```

If no request body, uses settings from database.

**Response:**
```json
{
  "message": "Scheduler started successfully (every 360 minutes)"
}
```

### `POST /api/scanner/scheduler/stop`

Stop the scheduled scanner.

**Response:**
```json
{
  "message": "Scheduler stopped successfully"
}
```

### `POST /api/scanner/watcher/start`

Start the file watcher.

**Request (optional):**
```json
{
  "enabled": true,
  "paths": ["/media/anime"],
  "recursive": true
}
```

If no request body, uses settings from database.

**Response:**
```json
{
  "message": "File watcher started successfully"
}
```

**Errors:**
- `400`: No library paths configured

### `POST /api/scanner/watcher/stop`

Stop the file watcher.

**Response:**
```json
{
  "message": "File watcher stopped successfully"
}
```

### `POST /api/scanner/analyze`

Analyze a single file with ffprobe.

**Query Parameters:**
- `file_path` (string, required): Path to file

**Response:**
```json
{
  "file_path": "/media/anime/episode.mkv",
  "audio_tracks": [
    {
      "index": 0,
      "codec": "aac",
      "language": "jpn",
      "channels": 2
    }
  ],
  "embedded_subtitles": [],
  "external_subtitles": [
    {
      "path": "/media/anime/episode.en.srt",
      "language": "eng"
    }
  ],
  "duration_seconds": 1440.5,
  "is_video": true
}
```

**Errors:**
- `400`: Path is not a file
- `404`: File not found

---

## Settings API

Base path: `/api/settings`

### `GET /api/settings`

Get all settings or filter by category.

**Query Parameters:**
- `category` (string, optional): Filter by category (`general`, `workers`, `transcription`, `scanner`, `bazarr`)

**Response:**
```json
[
  {
    "id": 1,
    "key": "worker_cpu_count",
    "value": "1",
    "description": "Number of CPU workers",
    "category": "workers",
    "value_type": "integer",
    "created_at": "2025-01-12T10:00:00",
    "updated_at": "2025-01-12T12:00:00"
  }
]
```

### `GET /api/settings/{key}`

Get a specific setting.

**Path Parameters:**
- `key` (string): Setting key

**Response:** Setting object (same as list item)

**Errors:**
- `404`: Setting not found

### `PUT /api/settings/{key}`

Update a setting value.

**Path Parameters:**
- `key` (string): Setting key

**Request:**
```json
{
  "value": "2"
}
```

**Response:** Updated setting object

**Errors:**
- `404`: Setting not found

### `POST /api/settings/bulk-update`

Update multiple settings at once.

**Request:**
```json
{
  "settings": {
    "worker_cpu_count": "2",
    "worker_gpu_count": "1",
    "scanner_enabled": "true"
  }
}
```

**Response:**
```json
{
  "message": "Updated 3 settings successfully"
}
```

### `POST /api/settings`

Create a new setting.

**Request:**
```json
{
  "key": "custom_setting",
  "value": "value",
  "description": "Custom setting description",
  "category": "general",
  "value_type": "string"
}
```

**Response:** Created setting (201)

**Errors:**
- `409`: Setting already exists

### `DELETE /api/settings/{key}`

Delete a setting.

**Path Parameters:**
- `key` (string): Setting key

**Response:**
```json
{
  "message": "Setting 'custom_setting' deleted successfully"
}
```

**Errors:**
- `404`: Setting not found

### `POST /api/settings/init-defaults`

Initialize all default settings (safe to call multiple times).

**Response:**
```json
{
  "message": "Default settings initialized successfully"
}
```

---

## System Resources API

Base path: `/api/system`

### `GET /api/system/resources`

Get all system resources (CPU, RAM, GPU).

**Response:**
```json
{
  "cpu": {
    "usage_percent": 25.5,
    "count_logical": 16,
    "count_physical": 8,
    "frequency_mhz": 3600.0
  },
  "memory": {
    "total_gb": 32.0,
    "used_gb": 12.5,
    "free_gb": 19.5,
    "usage_percent": 39.1
  },
  "gpus": [
    {
      "id": 0,
      "name": "NVIDIA GeForce RTX 3080",
      "memory_total_mb": 10240,
      "memory_used_mb": 2048,
      "memory_free_mb": 8192,
      "utilization_percent": 15
    }
  ]
}
```

### `GET /api/system/cpu`

Get CPU information only.

**Response:**
```json
{
  "usage_percent": 25.5,
  "count_logical": 16,
  "count_physical": 8,
  "frequency_mhz": 3600.0
}
```

### `GET /api/system/memory`

Get memory information only.

**Response:**
```json
{
  "total_gb": 32.0,
  "used_gb": 12.5,
  "free_gb": 19.5,
  "usage_percent": 39.1
}
```

### `GET /api/system/gpus`

Get all GPUs information.

**Response:**
```json
[
  {
    "id": 0,
    "name": "NVIDIA GeForce RTX 3080",
    "memory_total_mb": 10240,
    "memory_used_mb": 2048,
    "memory_free_mb": 8192,
    "utilization_percent": 15
  }
]
```

### `GET /api/system/gpu/{device_id}`

Get specific GPU information.

**Path Parameters:**
- `device_id` (int): GPU device ID

**Response:** GPU object (same as list item)

---

## Filesystem API

Base path: `/api/filesystem`

### `GET /api/filesystem/browse`

Browse filesystem directories.

**Query Parameters:**
- `path` (string, default="/"): Path to browse

**Response:**
```json
{
  "current_path": "/media",
  "parent_path": "/",
  "items": [
    {
      "name": "anime",
      "path": "/media/anime",
      "is_directory": true,
      "is_readable": true
    },
    {
      "name": "movies",
      "path": "/media/movies",
      "is_directory": true,
      "is_readable": true
    }
  ]
}
```

**Errors:**
- `400`: Path is not a directory
- `403`: Permission denied
- `404`: Path does not exist

### `GET /api/filesystem/common-paths`

Get list of common starting paths.

**Response:**
```json
[
  {
    "name": "/",
    "path": "/",
    "is_directory": true,
    "is_readable": true
  },
  {
    "name": "/media",
    "path": "/media",
    "is_directory": true,
    "is_readable": true
  }
]
```

---

## Setup Wizard API

Base path: `/api/setup`

### `GET /api/setup/status`

Check setup status.

**Response:**
```json
{
  "is_first_run": true,
  "setup_completed": false
}
```

### `POST /api/setup/standalone`

Configure standalone mode.

**Request:**
```json
{
  "library_paths": ["/media/anime", "/media/movies"],
  "scan_rules": [
    {
      "name": "Japanese to Spanish",
      "audio_language_is": "jpn",
      "missing_external_subtitle_lang": "spa",
      "target_language": "spa",
      "action_type": "transcribe"
    }
  ],
  "worker_config": {
    "count": 1,
    "type": "cpu"
  },
  "scanner_config": {
    "interval_minutes": 360
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Standalone mode configured successfully",
  "bazarr_info": null
}
```

### `POST /api/setup/bazarr-slave`

Configure Bazarr slave mode (generates API key).

**Request:** (empty body)

**Response:**
```json
{
  "success": true,
  "message": "Bazarr slave mode configured successfully",
  "bazarr_info": {
    "mode": "bazarr_slave",
    "host": "127.0.0.1",
    "port": 8000,
    "api_key": "generated_api_key_here",
    "provider_url": "http://127.0.0.1:8000"
  }
}
```

### `POST /api/setup/skip`

Skip setup wizard (for advanced users).

**Response:**
```json
{
  "message": "Setup wizard skipped"
}
```

---

## Bazarr Provider API (In Development)

> **Note:** These endpoints are functional but the full Bazarr integration is still in development.

### `POST /asr`

Transcription/translation endpoint (Bazarr compatibility).

### `POST /detect-language`

Language detection endpoint.

### `GET /status`

Provider status.

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Resource created |
| 400 | Bad request (invalid parameters) |
| 403 | Forbidden (permission denied) |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource) |
| 500 | Internal server error |

---

## Examples

### cURL Examples

```bash
# Get system status
curl http://localhost:8000/api/status

# Create a transcription job
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/media/anime/episode.mkv",
    "file_name": "episode.mkv",
    "target_lang": "spa",
    "quality_preset": "fast"
  }'

# Add a GPU worker
curl -X POST http://localhost:8000/api/workers \
  -H "Content-Type: application/json" \
  -d '{
    "worker_type": "gpu",
    "device_id": 0
  }'

# Trigger manual scan
curl -X POST http://localhost:8000/api/scanner/scan

# Update a setting
curl -X PUT http://localhost:8000/api/settings/worker_cpu_count \
  -H "Content-Type: application/json" \
  -d '{"value": "2"}'
```

### Python Example

```python
import requests

BASE_URL = "http://localhost:8000"

# Create a job
response = requests.post(
    f"{BASE_URL}/api/jobs",
    json={
        "file_path": "/media/anime/episode.mkv",
        "file_name": "episode.mkv",
        "target_lang": "spa",
        "quality_preset": "fast"
    }
)

job = response.json()
print(f"Job created: {job['id']}")

# Check job status
response = requests.get(f"{BASE_URL}/api/jobs/{job['id']}")
status = response.json()
print(f"Job status: {status['status']} - {status['progress']}%")

# Get system resources
response = requests.get(f"{BASE_URL}/api/system/resources")
resources = response.json()
print(f"CPU: {resources['cpu']['usage_percent']}%")
print(f"RAM: {resources['memory']['usage_percent']}%")
```

---

## Notes

- All dates are in ISO 8601 UTC format
- Languages use ISO 639-2 (3-letter codes): `jpn`, `eng`, `spa`, `fra`, etc.
- Pagination uses 1-based indexing (first page = 1)
- Worker IDs are auto-generated unique strings
- Jobs are deduplicated by `file_path` (no duplicate jobs for same file)
