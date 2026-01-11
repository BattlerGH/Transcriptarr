# TranscriptorIO Backend

This is the redesigned backend for TranscriptorIO, a complete fork of SubGen with modern asynchronous architecture.

## 🎯 Goal

Replace SubGen's synchronous non-persistent system with a modern Tdarr-inspired architecture:
- ✅ Persistent queue (SQLite/PostgreSQL/MariaDB)
- ✅ Asynchronous processing
- ✅ Job prioritization
- ✅ Complete state visibility
- ✅ No Bazarr timeouts

## 📁 Structure

```
backend/
├── core/
│   ├── database.py       # Multi-backend database management
│   ├── models.py         # SQLAlchemy models (Job, etc.)
│   ├── queue_manager.py  # Asynchronous persistent queue
│   └── __init__.py
├── api/                  # (coming soon) FastAPI endpoints
├── config.py            # Centralized configuration with Pydantic
└── README.md            # This file
```

## 🚀 Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure .env

Copy `.env.example` to `.env` and adjust as needed:

```bash
cp .env.example .env
```

#### Database Options

**SQLite (default)**:
```env
DATABASE_URL=sqlite:///./transcriptarr.db
```

**PostgreSQL**:
```bash
pip install psycopg2-binary
```
```env
DATABASE_URL=postgresql://user:password@localhost:5432/transcriptarr
```

**MariaDB/MySQL**:
```bash
pip install pymysql
```
```env
DATABASE_URL=mariadb+pymysql://user:password@localhost:3306/transcriptarr
```

### 3. Choose operation mode

**Standalone Mode** (automatically scans your library):
```env
TRANSCRIPTARR_MODE=standalone
LIBRARY_PATHS=/media/anime|/media/movies
AUTO_SCAN_ENABLED=True
SCAN_INTERVAL_MINUTES=30
```

**Provider Mode** (receives jobs from Bazarr):
```env
TRANSCRIPTARR_MODE=provider
BAZARR_URL=http://bazarr:6767
BAZARR_API_KEY=your_api_key
```

**Hybrid Mode** (both simultaneously):
```env
TRANSCRIPTARR_MODE=standalone,provider
```

## 🧪 Testing

Run the test script to verify everything works:

```bash
python test_backend.py
```

This will verify:
- ✓ Configuration loading
- ✓ Database connection
- ✓ Table creation
- ✓ Queue operations (add, get, deduplicate)

## 📊 Implemented Components

### config.py
- Centralized configuration with Pydantic
- Automatic environment variable validation
- Multi-backend database support
- Operation mode configuration

### database.py
- Connection management with SQLAlchemy
- Support for SQLite, PostgreSQL, MariaDB
- Backend-specific optimizations
  - SQLite: WAL mode, optimized cache
  - PostgreSQL: connection pooling, pre-ping
  - MariaDB: utf8mb4 charset, pooling
- Health checks and statistics

### models.py
- Complete `Job` model with:
  - States: queued, processing, completed, failed, cancelled
  - Stages: pending, detecting_language, transcribing, translating, etc.
  - Quality presets: fast, balanced, best
  - Progress tracking (0-100%)
  - Complete timestamps
  - Retry logic
  - Worker assignment
- Optimized indexes for common queries

### queue_manager.py
- Thread-safe persistent queue
- Job prioritization
- Duplicate detection
- Automatic retry for failed jobs
- Real-time statistics
- Automatic cleanup of old jobs

## 🔄 Comparison with SubGen

| Feature | SubGen | TranscriptorIO |
|---------|--------|----------------|
| Queue | In-memory (lost on restart) | **Persistent in DB** |
| Processing | Synchronous (blocks threads) | **Asynchronous** |
| Prioritization | No | **Yes (configurable)** |
| Visibility | No progress/ETA | **Progress + real-time ETA** |
| Deduplication | Basic (memory only) | **Persistent + intelligent** |
| Retries | No | **Automatic with limit** |
| Database | No | **SQLite/PostgreSQL/MariaDB** |
| Bazarr Timeouts | Yes (>5min = 24h throttle) | **No (async)** |

## 📝 Next Steps

1. **Worker Pool** - Asynchronous worker system
2. **REST API** - FastAPI endpoints for management
3. **WebSocket** - Real-time updates
4. **Transcriber** - Whisper wrapper with progress callbacks
5. **Bazarr Provider** - Improved async provider
6. **Standalone Scanner** - Automatic library scanning

## 🐛 Troubleshooting

### Error: "No module named 'backend'"

Make sure to run scripts from the project root:
```bash
cd /home/dasemu/Hacking/Transcriptarr
python test_backend.py
```

### Error: Database locked (SQLite)

SQLite is configured with WAL mode for better concurrency. If you still have issues, consider using PostgreSQL for production.

### Error: pydantic.errors.ConfigError

Verify that all required variables are in your `.env`:
```bash
cp .env.example .env
# Edit .env with your values
```

## 📚 Documentation

See `CLAUDE.md` for complete architecture and project roadmap.