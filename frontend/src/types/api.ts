// API Types matching backend models

export interface SystemStatus {
  system: {
    status: string
    uptime_seconds: number | null
  }
  workers: WorkerPoolStats
  queue: QueueStats
  scanner: ScannerStatus
}

export interface WorkerPoolStats {
  total_workers: number
  cpu_workers: number
  gpu_workers: number
  idle_workers: number
  busy_workers: number
  stopped_workers: number
  error_workers: number
  total_jobs_completed: number
  total_jobs_failed: number
  uptime_seconds: number | null
  is_running: boolean
}

export interface Worker {
  worker_id: string
  worker_type: 'cpu' | 'gpu'
  device_id: number | null
  status: 'idle' | 'busy' | 'stopped' | 'error'
  current_job_id: string | null
  jobs_completed: number
  jobs_failed: number
  uptime_seconds: number
  current_job_progress: number
  current_job_eta: number | null
}

export interface Job {
  id: string
  file_path: string
  file_name: string
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled'
  priority: number
  source_lang: string | null
  target_lang: string | null
  quality_preset: 'fast' | 'balanced' | 'best'
  transcribe_or_translate: string
  progress: number
  current_stage: string | null
  eta_seconds: number | null
  created_at: string | null
  started_at: string | null
  completed_at: string | null
  output_path: string | null
  segments_count: number | null
  error: string | null
  retry_count: number
  worker_id: string | null
  vram_used_mb: number | null
  processing_time_seconds: number | null
  model_used: string | null
  device_used: string | null
}

export interface JobList {
  jobs: Job[]
  total: number
  page: number
  page_size: number
}

export interface QueueStats {
  total_jobs: number
  queued: number
  processing: number
  completed: number
  failed: number
  cancelled: number
}

export interface ScanRule {
  id: number
  name: string
  enabled: boolean
  priority: number
  conditions: ScanRuleConditions
  action: ScanRuleAction
  created_at: string | null
  updated_at: string | null
}

export interface ScanRuleConditions {
  audio_language_is: string | null
  audio_language_not: string | null
  audio_track_count_min: number | null
  has_embedded_subtitle_lang: string | null
  missing_embedded_subtitle_lang: string | null
  missing_external_subtitle_lang: string | null
  file_extension: string | null
}

export interface ScanRuleAction {
  action_type: 'transcribe' | 'translate'
  target_language: string
  quality_preset: 'fast' | 'balanced' | 'best'
  job_priority: number
}

export interface ScannerStatus {
  scheduler_enabled: boolean
  scheduler_running: boolean
  next_scan_time: string | null
  watcher_enabled: boolean
  watcher_running: boolean
  watched_paths: string[]
  last_scan_time: string | null
  total_scans: number
}

export interface ScanResult {
  scanned_files: number
  matched_files: number
  jobs_created: number
  skipped_files: number
  paths_scanned: string[]
}

// Request types
export interface CreateJobRequest {
  file_path: string
  file_name: string
  source_lang?: string
  target_lang: string
  quality_preset?: 'fast' | 'balanced' | 'best'
  transcribe_or_translate?: string
  priority?: number
  is_manual_request?: boolean
}

export interface AddWorkerRequest {
  worker_type: 'cpu' | 'gpu'
  device_id?: number
}

export interface CreateScanRuleRequest {
  name: string
  enabled: boolean
  priority: number
  conditions: ScanRuleConditions
  action: ScanRuleAction
}

export interface ScanRequest {
  paths: string[]
  recursive: boolean
}

