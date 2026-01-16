# TranscriptorIO REST API

Documentación completa de las APIs REST del backend de TranscriptorIO.

## 🚀 Inicio Rápido

### Ejecutar el servidor

```bash
# Usando el CLI
python backend/cli.py server --host 0.0.0.0 --port 8000

# Con auto-reload (desarrollo)
python backend/cli.py server --reload

# Con múltiples workers (producción)
python backend/cli.py server --workers 4
```

### Documentación interactiva

Una vez iniciado el servidor, accede a:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📋 Endpoints

### System Status

#### `GET /`
Información básica de la API.

**Response:**
```json
{
  "name": "TranscriptorIO API",
  "version": "1.0.0",
  "status": "running"
}
```

#### `GET /health`
Health check para monitoring.

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "workers": 2,
  "queue_size": 5
}
```

#### `GET /api/status`
Estado completo del sistema.

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
    "total": 100,
    "queued": 5,
    "processing": 2,
    "completed": 90,
    "failed": 3
  },
  "scanner": {
    "scheduler_running": true,
    "next_scan_time": "2026-01-13T02:00:00",
    "watcher_running": true
  }
}
```

---

## 👷 Workers API (`/api/workers`)

### `GET /api/workers`
Lista todos los workers activos.

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
Estadísticas del pool de workers.

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
Obtener estado de un worker específico.

**Response:** Same as individual worker in list

### `POST /api/workers`
Añadir un nuevo worker al pool.

**Request:**
```json
{
  "worker_type": "gpu",
  "device_id": 0
}
```

**Response:** Worker status object

### `DELETE /api/workers/{worker_id}`
Remover un worker del pool.

**Query Params:**
- `timeout` (float, default=30.0): Timeout en segundos

**Response:**
```json
{
  "message": "Worker worker-cpu-0 removed successfully"
}
```

### `POST /api/workers/pool/start`
Iniciar el pool de workers.

**Query Params:**
- `cpu_workers` (int, default=0)
- `gpu_workers` (int, default=0)

**Response:**
```json
{
  "message": "Worker pool started: 1 CPU workers, 1 GPU workers"
}
```

### `POST /api/workers/pool/stop`
Detener el pool de workers.

**Query Params:**
- `timeout` (float, default=30.0)

**Response:**
```json
{
  "message": "Worker pool stopped successfully"
}
```

---

## 📋 Jobs API (`/api/jobs`)

### `GET /api/jobs`
Lista de trabajos con paginación.

**Query Params:**
- `status_filter` (optional): queued, processing, completed, failed, cancelled
- `page` (int, default=1): Número de página
- `page_size` (int, default=50): Items por página

**Response:**
```json
{
  "jobs": [
    {
      "id": "abc123",
      "file_path": "/media/anime/episode.mkv",
      "file_name": "episode.mkv",
      "status": "completed",
      "priority": 10,
      "source_lang": "ja",
      "target_lang": "es",
      "quality_preset": "fast",
      "transcribe_or_translate": "transcribe",
      "progress": 100.0,
      "current_stage": "finalizing",
      "eta_seconds": null,
      "created_at": "2026-01-12T10:00:00",
      "started_at": "2026-01-12T10:00:05",
      "completed_at": "2026-01-12T10:05:30",
      "output_path": "/media/anime/episode.es.srt",
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
Estadísticas de la cola.

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
Obtener un trabajo específico.

**Response:** Job object (same as in list)

### `POST /api/jobs`
Crear un nuevo trabajo de transcripción.

**Request:**
```json
{
  "file_path": "/media/anime/Attack on Titan S04E01.mkv",
  "file_name": "Attack on Titan S04E01.mkv",
  "source_lang": "ja",
  "target_lang": "es",
  "quality_preset": "fast",
  "transcribe_or_translate": "transcribe",
  "priority": 10,
  "is_manual_request": true
}
```

**Response:** Created job object

### `POST /api/jobs/{job_id}/retry`
Reintentar un trabajo fallido.

**Response:** Updated job object

### `DELETE /api/jobs/{job_id}`
Cancelar un trabajo.

**Response:**
```json
{
  "message": "Job abc123 cancelled successfully"
}
```

### `POST /api/jobs/queue/clear`
Limpiar trabajos completados.

**Response:**
```json
{
  "message": "Cleared 42 completed jobs"
}
```

---

## 📏 Scan Rules API (`/api/scan-rules`)

### `GET /api/scan-rules`
Lista todas las reglas de escaneo.

**Query Params:**
- `enabled_only` (bool, default=false): Solo reglas habilitadas

**Response:**
```json
[
  {
    "id": 1,
    "name": "Japanese anime without Spanish subs",
    "enabled": true,
    "priority": 10,
    "conditions": {
      "audio_language_is": "ja",
      "audio_language_not": null,
      "audio_track_count_min": null,
      "has_embedded_subtitle_lang": null,
      "missing_embedded_subtitle_lang": "es",
      "missing_external_subtitle_lang": "es",
      "file_extension": ".mkv,.mp4"
    },
    "action": {
      "action_type": "transcribe",
      "target_language": "es",
      "quality_preset": "fast",
      "job_priority": 5
    },
    "created_at": "2026-01-12T10:00:00",
    "updated_at": null
  }
]
```

### `GET /api/scan-rules/{rule_id}`
Obtener una regla específica.

**Response:** Rule object (same as in list)

### `POST /api/scan-rules`
Crear una nueva regla de escaneo.

**Request:**
```json
{
  "name": "Japanese anime without Spanish subs",
  "enabled": true,
  "priority": 10,
  "conditions": {
    "audio_language_is": "ja",
    "missing_embedded_subtitle_lang": "es",
    "missing_external_subtitle_lang": "es",
    "file_extension": ".mkv,.mp4"
  },
  "action": {
    "action_type": "transcribe",
    "target_language": "es",
    "quality_preset": "fast",
    "job_priority": 5
  }
}
```

**Response:** Created rule object

### `PUT /api/scan-rules/{rule_id}`
Actualizar una regla.

**Request:** Same as POST (all fields optional)

**Response:** Updated rule object

### `DELETE /api/scan-rules/{rule_id}`
Eliminar una regla.

**Response:**
```json
{
  "message": "Scan rule 1 deleted successfully"
}
```

### `POST /api/scan-rules/{rule_id}/toggle`
Activar/desactivar una regla.

**Response:** Updated rule object

---

## 🔍 Scanner API (`/api/scanner`)

### `GET /api/scanner/status`
Estado del scanner.

**Response:**
```json
{
  "scheduler_enabled": true,
  "scheduler_running": true,
  "next_scan_time": "2026-01-13T02:00:00",
  "watcher_enabled": true,
  "watcher_running": true,
  "watched_paths": ["/media/anime", "/media/movies"],
  "last_scan_time": "2026-01-12T02:00:00",
  "total_scans": 1523
}
```

### `POST /api/scanner/scan`
Ejecutar escaneo manual.

**Request:**
```json
{
  "paths": ["/media/anime", "/media/movies"],
  "recursive": true
}
```

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

### `POST /api/scanner/scheduler/start`
Iniciar escaneo programado.

**Request:**
```json
{
  "enabled": true,
  "cron_expression": "0 2 * * *",
  "paths": ["/media/anime"],
  "recursive": true
}
```

**Response:**
```json
{
  "message": "Scheduler started successfully"
}
```

### `POST /api/scanner/scheduler/stop`
Detener escaneo programado.

**Response:**
```json
{
  "message": "Scheduler stopped successfully"
}
```

### `POST /api/scanner/watcher/start`
Iniciar observador de archivos.

**Request:**
```json
{
  "enabled": true,
  "paths": ["/media/anime"],
  "recursive": true
}
```

**Response:**
```json
{
  "message": "File watcher started successfully"
}
```

### `POST /api/scanner/watcher/stop`
Detener observador de archivos.

**Response:**
```json
{
  "message": "File watcher stopped successfully"
}
```

### `POST /api/scanner/analyze`
Analizar un archivo específico.

**Query Params:**
- `file_path` (required): Ruta al archivo

**Response:**
```json
{
  "file_path": "/media/anime/episode.mkv",
  "audio_tracks": [
    {
      "index": 0,
      "codec": "aac",
      "language": "ja",
      "channels": 2
    }
  ],
  "embedded_subtitles": [],
  "external_subtitles": [
    {
      "path": "/media/anime/episode.en.srt",
      "language": "en"
    }
  ],
  "duration_seconds": 1440.5,
  "is_video": true
}
```

---

## 🔐 Autenticación

> **TODO**: Implementar autenticación con JWT tokens

---

## 📊 Códigos de Error

- `200 OK`: Éxito
- `201 Created`: Recurso creado
- `400 Bad Request`: Parámetros inválidos
- `404 Not Found`: Recurso no encontrado
- `409 Conflict`: Conflicto (ej: duplicado)
- `500 Internal Server Error`: Error del servidor

---

## 🧪 Testing

### cURL Examples

```bash
# Get system status
curl http://localhost:8000/api/status

# Create a job
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "/media/anime/episode.mkv",
    "file_name": "episode.mkv",
    "target_lang": "es",
    "quality_preset": "fast"
  }'

# Add a GPU worker
curl -X POST http://localhost:8000/api/workers \
  -H "Content-Type: application/json" \
  -d '{
    "worker_type": "gpu",
    "device_id": 0
  }'
```

### Python Example

```python
import requests

# Base URL
BASE_URL = "http://localhost:8000"

# Create a job
response = requests.post(
    f"{BASE_URL}/api/jobs",
    json={
        "file_path": "/media/anime/episode.mkv",
        "file_name": "episode.mkv",
        "target_lang": "es",
        "quality_preset": "fast"
    }
)

job = response.json()
print(f"Job created: {job['id']}")

# Check job status
response = requests.get(f"{BASE_URL}/api/jobs/{job['id']}")
status = response.json()
print(f"Job status: {status['status']} - {status['progress']}%")
```

---

## 📝 Notas

- Todas las fechas están en formato ISO 8601 UTC
- Los idiomas usan códigos ISO 639-1 (2 letras: ja, en, es, fr, etc.)
- La paginación usa índices base-1 (primera página = 1)
- Los workers se identifican por ID único generado automáticamente

