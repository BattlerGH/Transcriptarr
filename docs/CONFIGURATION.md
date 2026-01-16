# TranscriptorIO Configuration

Complete documentation for the configuration system.

## Table of Contents

- [Overview](#overview)
- [Configuration Methods](#configuration-methods)
- [Settings Categories](#settings-categories)
- [All Settings Reference](#all-settings-reference)
- [Environment Variables](#environment-variables)
- [Setup Wizard](#setup-wizard)
- [API Configuration](#api-configuration)

---

## Overview

TranscriptorIO uses a **database-backed configuration system**. All settings are stored in the `system_settings` table and can be managed through:

1. **Setup Wizard** (first run)
2. **Web UI** (Settings page)
3. **REST API** (`/api/settings`)
4. **CLI** (for advanced users)

This approach provides:
- Persistent configuration across restarts
- Runtime configuration changes without restart
- Category-based organization
- Type validation and parsing

---

## Configuration Methods

### 1. Setup Wizard (Recommended for First Run)

```bash
# Runs automatically on first server start
python backend/cli.py server

# Or run manually anytime
python backend/cli.py setup
```

The wizard guides you through:
- **Operation mode selection** (Standalone or Bazarr provider)
- **Library paths configuration**
- **Initial scan rules**
- **Worker configuration** (CPU/GPU counts)
- **Scanner schedule**

### 2. Web UI (Recommended for Daily Use)

Navigate to **Settings** in the web interface (`http://localhost:8000/settings`).

Features:
- Settings grouped by category tabs
- Descriptions for each setting
- Change detection (warns about unsaved changes)
- Bulk save functionality

### 3. REST API (For Automation/Integration)

```bash
# Get all settings
curl http://localhost:8000/api/settings

# Get settings by category
curl http://localhost:8000/api/settings?category=workers

# Update a setting
curl -X PUT http://localhost:8000/api/settings/worker_cpu_count \
  -H "Content-Type: application/json" \
  -d '{"value": "2"}'

# Bulk update
curl -X POST http://localhost:8000/api/settings/bulk-update \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "worker_cpu_count": "2",
      "worker_gpu_count": "1"
    }
  }'
```

---

## Settings Categories

| Category | Description |
|----------|-------------|
| `general` | Operation mode, library paths, API server |
| `workers` | CPU/GPU worker configuration |
| `transcription` | Whisper model and transcription options |
| `subtitles` | Subtitle naming and formatting |
| `skip` | Skip conditions for files |
| `scanner` | Library scanner configuration |
| `bazarr` | Bazarr provider integration |
| `advanced` | Advanced options (path mapping, etc.) |

---

## All Settings Reference

### General Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `operation_mode` | string | `standalone` | Operation mode: `standalone`, `provider`, or `standalone,provider` |
| `library_paths` | list | `""` | Comma-separated library paths to scan |
| `api_host` | string | `0.0.0.0` | API server host |
| `api_port` | integer | `8000` | API server port |
| `debug` | boolean | `false` | Enable debug mode |

### Worker Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `worker_cpu_count` | integer | `0` | Number of CPU workers to start on boot |
| `worker_gpu_count` | integer | `0` | Number of GPU workers to start on boot |
| `concurrent_transcriptions` | integer | `2` | Maximum concurrent transcriptions |
| `worker_healthcheck_interval` | integer | `60` | Worker health check interval (seconds) |
| `worker_auto_restart` | boolean | `true` | Auto-restart failed workers |
| `clear_vram_on_complete` | boolean | `true` | Clear VRAM after job completion |

### Transcription Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `whisper_model` | string | `medium` | Whisper model: `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo` |
| `model_path` | string | `./models` | Path to store Whisper models |
| `transcribe_device` | string | `cpu` | Device: `cpu`, `cuda`, `gpu` |
| `cpu_compute_type` | string | `auto` | CPU compute type: `auto`, `int8`, `float32` |
| `gpu_compute_type` | string | `auto` | GPU compute type: `auto`, `float16`, `float32`, `int8_float16`, `int8` |
| `whisper_threads` | integer | `4` | Number of CPU threads for Whisper |
| `transcribe_or_translate` | string | `transcribe` | Default mode: `transcribe` or `translate` |
| `word_level_highlight` | boolean | `false` | Enable word-level highlighting |
| `detect_language_length` | integer | `30` | Seconds of audio for language detection |
| `detect_language_offset` | integer | `0` | Offset for language detection sample |

### Whisper Models

| Model | Size | Speed | Quality | VRAM |
|-------|------|-------|---------|------|
| `tiny` | 39M | Fastest | Basic | ~1GB |
| `base` | 74M | Very Fast | Fair | ~1GB |
| `small` | 244M | Fast | Good | ~2GB |
| `medium` | 769M | Medium | Great | ~5GB |
| `large-v3` | 1.5G | Slow | Excellent | ~10GB |
| `large-v3-turbo` | 809M | Fast | Excellent | ~6GB |

### Subtitle Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `subtitle_language_name` | string | `""` | Custom subtitle language name |
| `subtitle_language_naming_type` | string | `ISO_639_2_B` | Naming type: `ISO_639_1`, `ISO_639_2_T`, `ISO_639_2_B`, `NAME`, `NATIVE` |
| `custom_regroup` | string | `cm_sl=84_sl=42++++++1` | Custom regrouping algorithm |

**Language Naming Types:**

| Type | Example (Spanish) |
|------|-------------------|
| ISO_639_1 | `es` |
| ISO_639_2_T | `spa` |
| ISO_639_2_B | `spa` |
| NAME | `Spanish` |
| NATIVE | `Espanol` |

### Skip Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `skip_if_external_subtitles_exist` | boolean | `false` | Skip if any external subtitle exists |
| `skip_if_target_subtitles_exist` | boolean | `true` | Skip if target language subtitle exists |
| `skip_if_internal_subtitles_language` | string | `""` | Skip if internal subtitle in this language |
| `skip_subtitle_languages` | list | `""` | Pipe-separated language codes to skip |
| `skip_if_audio_languages` | list | `""` | Skip if audio track is in these languages |
| `skip_unknown_language` | boolean | `false` | Skip files with unknown audio language |
| `skip_only_subgen_subtitles` | boolean | `false` | Only skip SubGen-generated subtitles |

### Scanner Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `scanner_enabled` | boolean | `true` | Enable library scanner |
| `scanner_cron` | string | `0 2 * * *` | Cron expression for scheduled scans |
| `scanner_schedule_interval_minutes` | integer | `360` | Scan interval in minutes (6 hours) |
| `watcher_enabled` | boolean | `false` | Enable real-time file watcher |
| `auto_scan_enabled` | boolean | `false` | Enable automatic scheduled scanning |

### Bazarr Provider Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `bazarr_provider_enabled` | boolean | `false` | Enable Bazarr provider mode |
| `bazarr_url` | string | `http://bazarr:6767` | Bazarr server URL |
| `bazarr_api_key` | string | `""` | Bazarr API key (auto-generated) |
| `provider_timeout_seconds` | integer | `600` | Provider request timeout |
| `provider_callback_enabled` | boolean | `true` | Enable callback on completion |
| `provider_polling_interval` | integer | `30` | Polling interval for jobs |

### Advanced Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `force_detected_language_to` | string | `""` | Force detected language to specific code |
| `preferred_audio_languages` | list | `eng` | Pipe-separated preferred audio languages |
| `use_path_mapping` | boolean | `false` | Enable path mapping for network shares |
| `path_mapping_from` | string | `/tv` | Path mapping source |
| `path_mapping_to` | string | `/Volumes/TV` | Path mapping destination |
| `lrc_for_audio_files` | boolean | `true` | Generate LRC files for audio-only files |

---

## Environment Variables

The **only** environment variable required is `DATABASE_URL` in the `.env` file:

```bash
# SQLite (default, good for single-user)
DATABASE_URL=sqlite:///./transcriptarr.db

# PostgreSQL (recommended for production)
DATABASE_URL=postgresql://user:password@localhost:5432/transcriptarr

# MariaDB/MySQL
DATABASE_URL=mariadb+pymysql://user:password@localhost:3306/transcriptarr
```

**All other configuration** is stored in the database and managed through:
- Setup Wizard (first run)
- Web UI Settings page
- Settings API endpoints

This design ensures:
- No `.env` file bloat
- Runtime configuration changes without restart
- Centralized configuration management
- Easy backup (configuration is in the database)

---

## Setup Wizard

### Standalone Mode

For independent operation with local library scanning.

**Configuration Flow:**
1. Select library paths (e.g., `/media/anime`, `/media/movies`)
2. Create initial scan rules (e.g., "Japanese audio → Spanish subtitles")
3. Configure workers (CPU count, GPU count)
4. Set scanner interval (default: 6 hours)

**API Endpoint:** `POST /api/setup/standalone`

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

### Bazarr Slave Mode

For integration with Bazarr as a subtitle provider.

**Configuration Flow:**
1. Select Bazarr mode
2. System auto-generates API key
3. Displays connection info for Bazarr configuration

**API Endpoint:** `POST /api/setup/bazarr-slave`

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

---

## API Configuration

### Get All Settings

```bash
curl http://localhost:8000/api/settings
```

### Get by Category

```bash
curl "http://localhost:8000/api/settings?category=workers"
```

### Get Single Setting

```bash
curl http://localhost:8000/api/settings/worker_cpu_count
```

### Update Setting

```bash
curl -X PUT http://localhost:8000/api/settings/worker_cpu_count \
  -H "Content-Type: application/json" \
  -d '{"value": "2"}'
```

### Bulk Update

```bash
curl -X POST http://localhost:8000/api/settings/bulk-update \
  -H "Content-Type: application/json" \
  -d '{
    "settings": {
      "worker_cpu_count": "2",
      "worker_gpu_count": "1",
      "scanner_enabled": "true"
    }
  }'
```

### Create Custom Setting

```bash
curl -X POST http://localhost:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "key": "my_custom_setting",
    "value": "custom_value",
    "description": "My custom setting",
    "category": "advanced",
    "value_type": "string"
  }'
```

### Delete Setting

```bash
curl -X DELETE http://localhost:8000/api/settings/my_custom_setting
```

### Initialize Defaults

```bash
curl -X POST http://localhost:8000/api/settings/init-defaults
```

---

## Python Usage

```python
from backend.core.settings_service import settings_service

# Get setting with default
cpu_count = settings_service.get("worker_cpu_count", default=1)

# Set setting
settings_service.set("worker_cpu_count", 2)

# Bulk update
settings_service.bulk_update({
    "worker_cpu_count": "2",
    "scanner_enabled": "true"
})

# Get all settings in category
worker_settings = settings_service.get_by_category("workers")

# Initialize defaults (safe to call multiple times)
settings_service.init_default_settings()
```
