"""Library scanner with rule-based filtering and scheduling."""
import logging
import os
import time
from typing import List, Optional, Dict
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

from backend.core.database import database
from backend.core.queue_manager import queue_manager
from backend.core.models import QualityPreset
from backend.scanning.models import ScanRule
from backend.scanning.file_analyzer import FileAnalyzer, FileAnalysis
from backend.scanning.language_detector import language_detector
from backend.core.language_code import LanguageCode

logger = logging.getLogger(__name__)


class LibraryFileHandler(FileSystemEventHandler):
    """Watchdog handler for real-time file detection."""

    def __init__(self, scanner: "LibraryScanner"):
        """
        Initialize file handler.

        Args:
            scanner: Parent LibraryScanner instance
        """
        super().__init__()
        self.scanner = scanner

    def on_created(self, event: FileCreatedEvent):
        """
        Handle new file creation.

        Args:
            event: File creation event
        """
        if event.is_directory:
            return

        file_path = event.src_path

        # Check if it's a video file
        if not FileAnalyzer.is_video_file(file_path):
            return

        # Wait a bit for file to be fully written
        time.sleep(5)

        logger.info(f"New file detected: {file_path}")
        self.scanner.process_file(file_path)


class LibraryScanner:
    """
    Library scanner with rule-based filtering.

    Scans media libraries, analyzes files with ffprobe, and applies
    configurable rules to determine which files need transcription.

    Supports:
    - One-time manual scans
    - Scheduled periodic scans (cron-like)
    - Real-time file watching (Tdarr-style)
    """

    def __init__(self):
        """Initialize library scanner."""
        self.scheduler: Optional[BackgroundScheduler] = None
        self.file_observer: Optional[Observer] = None
        self.is_scanning = False
        self.last_scan_time: Optional[datetime] = None
        self.files_scanned = 0
        self.files_queued = 0

        logger.info("LibraryScanner initialized")

    def scan_libraries(self, paths: Optional[List[str]] = None) -> Dict:
        """
        Perform a one-time scan of library directories.

        Args:
            paths: List of directories to scan (uses config if None)

        Returns:
            Dictionary with scan statistics
        """
        if self.is_scanning:
            logger.warning("Scan already in progress")
            return {"error": "Scan already in progress"}

        self.is_scanning = True
        self.files_scanned = 0
        self.files_queued = 0
        scan_start = time.time()

        try:
            # Get paths from settings_service if not provided
            if paths is None:
                from backend.core.settings_service import settings_service
                library_paths = settings_service.get('library_paths', '')
                if not library_paths:
                    logger.error("No library paths configured")
                    return {"error": "No library paths configured"}
                # Handle both comma and pipe separators
                if '|' in library_paths:
                    paths = [p.strip() for p in library_paths.split("|") if p.strip()]
                else:
                    paths = [p.strip() for p in library_paths.split(",") if p.strip()]

            logger.info(f"Starting library scan: {len(paths)} paths")

            # Load all enabled rules
            rules = self._load_scan_rules()
            logger.info(f"Loaded {len(rules)} enabled scan rules")

            # Scan each path
            for path in paths:
                if not os.path.isdir(path):
                    logger.warning(f"Path not found or not a directory: {path}")
                    continue

                logger.info(f"Scanning: {path}")
                self._scan_directory(path, rules)

            scan_duration = time.time() - scan_start
            self.last_scan_time = datetime.now(timezone.utc)
            self._persist_scan_stats(files_in_this_scan=self.files_scanned)

            results = {
                "status": "completed",
                "files_scanned": self.files_scanned,
                "files_queued": self.files_queued,
                "duration_seconds": round(scan_duration, 2),
                "timestamp": self.last_scan_time.isoformat(),
            }

            logger.info(
                f"Scan completed: {self.files_scanned} files scanned, "
                f"{self.files_queued} jobs queued in {scan_duration:.1f}s"
            )

            return results

        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            return {"error": str(e)}

        finally:
            self.is_scanning = False

    def _scan_directory(self, directory: str, rules: List[ScanRule]):
        """
        Recursively scan a directory.

        Args:
            directory: Directory path
            rules: List of scan rules to apply
        """
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.files_scanned += 1

                    # Process file
                    self.process_file(file_path, rules)

        except Exception as e:
            logger.error(f"Error scanning directory {directory}: {e}")

    def process_file(
        self, file_path: str, rules: Optional[List[ScanRule]] = None
    ) -> bool:
        """
        Process a single file against scan rules.

        Args:
            file_path: Path to media file
            rules: Optional list of rules (will load if None)

        Returns:
            True if job was queued, False otherwise
        """
        try:
            # Analyze file
            analysis = FileAnalyzer.analyze_file(file_path)
            if not analysis:
                return False

            # Check if we need language detection
            if not analysis.default_audio_language or len(analysis.audio_languages) == 0:
                logger.info(
                    f"Audio language unknown for {analysis.file_name}, "
                    f"queuing language detection job"
                )
                return self._queue_language_detection_job(analysis)

            # Load rules if not provided
            if rules is None:
                rules = self._load_scan_rules()

            # Evaluate against rules
            matching_rule = self._evaluate_rules(analysis, rules)

            if matching_rule:
                # Queue job based on rule
                return self._queue_job_from_rule(analysis, matching_rule)

            return False

        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            return False

    def _evaluate_rules(
        self, file_analysis: FileAnalysis, rules: List[ScanRule]
    ) -> Optional[ScanRule]:
        """
        Evaluate file against rules (in priority order).

        Args:
            file_analysis: File analysis result
            rules: List of scan rules

        Returns:
            First matching rule or None
        """
        for rule in rules:
            if self._rule_matches(file_analysis, rule):
                logger.debug(f"File {file_analysis.file_name} matches rule: {rule.name}")
                return rule

        return None

    def _rule_matches(self, file_analysis: FileAnalysis, rule: ScanRule) -> bool:
        """
        Check if a file matches a scan rule.

        Args:
            file_analysis: File analysis
            rule: Scan rule

        Returns:
            True if all conditions match
        """
        # Check if rule has any conditions defined
        has_conditions = any([
            rule.file_extension,
            rule.audio_language_is,
            rule.audio_language_not,
            rule.audio_track_count_min,
            rule.has_embedded_subtitle_lang,
            rule.missing_embedded_subtitle_lang,
            rule.missing_external_subtitle_lang
        ])

        if not has_conditions:
            logger.warning(
                f"Rule '{rule.name}' has no conditions - will match ALL files. "
                f"This is probably not what you want!"
            )

        # Check file extension filter
        if rule.file_extension:
            if file_analysis.file_extension not in rule.file_extension_list:
                return False

        # Check audio language IS
        if rule.audio_language_is:
            target_lang = LanguageCode.from_string(rule.audio_language_is)

            # Check if file has the target language
            has_target_lang = target_lang in file_analysis.audio_languages

            # Also check if file has undefined language (None) - will need detection
            has_undefined_lang = None in file_analysis.audio_languages or \
                                 any(lang is None for lang in file_analysis.audio_languages)

            if not has_target_lang:
                # If language is undefined, try to detect it with Whisper
                if has_undefined_lang:
                    logger.info(
                        f"File {file_analysis.file_name} has undefined audio language - "
                        f"attempting detection with Whisper..."
                    )

                    detected_lang = language_detector.detect_language(file_analysis.file_path)

                    if detected_lang:
                        logger.info(
                            f"Detected language for {file_analysis.file_name}: {detected_lang}"
                        )

                        # Check if detected language matches rule
                        if detected_lang == target_lang:
                            logger.info(
                                f"✓ Detected language '{detected_lang}' matches rule '{rule.name}'"
                            )
                            # Update file_analysis with detected language for later use
                            if file_analysis.audio_tracks:
                                file_analysis.audio_tracks[0].language = detected_lang
                            return True  # Continue checking other conditions
                        else:
                            logger.debug(
                                f"Rule '{rule.name}' failed: detected '{detected_lang}' "
                                f"but expected '{rule.audio_language_is}'"
                            )
                            return False
                    else:
                        logger.warning(
                            f"Failed to detect language for {file_analysis.file_name} - skipping"
                        )
                        return False
                else:
                    # Language is defined but doesn't match
                    logger.debug(
                        f"Rule '{rule.name}' audio check failed for {file_analysis.file_name}: "
                        f"Expected '{rule.audio_language_is}' but found "
                        f"{[str(lang) if lang else 'und' for lang in file_analysis.audio_languages]}"
                    )
                    return False


        # Check audio language NOT
        if rule.audio_language_not:
            excluded_langs = [
                LanguageCode.from_string(lang) for lang in rule.audio_language_not_list
            ]
            if any(lang in file_analysis.audio_languages for lang in excluded_langs):
                return False

        # Check minimum audio tracks
        if rule.audio_track_count_min:
            if len(file_analysis.audio_tracks) < rule.audio_track_count_min:
                return False

        # Check HAS embedded subtitle
        if rule.has_embedded_subtitle_lang:
            required_lang = LanguageCode.from_string(rule.has_embedded_subtitle_lang)
            if not file_analysis.has_embedded_subtitle_language(required_lang):
                return False

        # Check MISSING embedded subtitle
        if rule.missing_embedded_subtitle_lang:
            excluded_lang = LanguageCode.from_string(rule.missing_embedded_subtitle_lang)
            if file_analysis.has_embedded_subtitle_language(excluded_lang):
                return False

        # Check MISSING external subtitle
        if rule.missing_external_subtitle_lang:
            excluded_lang = LanguageCode.from_string(rule.missing_external_subtitle_lang)
            if file_analysis.has_external_subtitle_language(excluded_lang):
                return False

        # All conditions matched
        logger.debug(
            f"File '{file_analysis.file_name}' matched rule '{rule.name}' "
            f"(priority: {rule.priority})"
        )
        return True

    def _queue_language_detection_job(self, file_analysis: FileAnalysis) -> bool:
        """
        Create and queue a language detection job for a file with unknown audio language.

        Args:
            file_analysis: File analysis

        Returns:
            True if job was queued successfully
        """
        try:
            from backend.core.models import JobType, JobStatus

            # Check if there's already a completed detection job for this file
            with database.get_session() as session:
                from backend.core.models import Job
                existing_detection = session.query(Job).filter(
                    Job.file_path == file_analysis.file_path,
                    Job.job_type == JobType.LANGUAGE_DETECTION,
                    Job.status == JobStatus.COMPLETED
                ).first()

                if existing_detection:
                    logger.info(
                        f"✓ Language already detected for {file_analysis.file_name}, "
                        f"checking for transcription rules..."
                    )
                    # Extract detected language from SRT content
                    if existing_detection.srt_content:
                        # Format: "Language detected: ja (Japanese)\nConfidence: 99%"
                        lines = existing_detection.srt_content.split('\n')
                        if lines:
                            lang_line = lines[0]
                            if 'Language detected:' in lang_line:
                                lang_code = lang_line.split(':')[1].strip().split(' ')[0]
                                # Trigger rule checking with detected language
                                self._check_and_queue_transcription_for_file(
                                    file_analysis.file_path, lang_code
                                )
                    return False

            # Add language detection job with high priority
            job = queue_manager.add_job(
                file_path=file_analysis.file_path,
                file_name=file_analysis.file_name,
                source_lang=None,  # To be detected
                target_lang=None,
                quality_preset=QualityPreset.FAST,
                priority=15,  # Higher than normal transcription (0-10) but lower than manual (20+)
                transcribe_or_translate="transcribe",
                job_type=JobType.LANGUAGE_DETECTION,
            )

            if job:
                logger.info(
                    f"✓ Queued LANGUAGE DETECTION job {job.id} for {file_analysis.file_name}"
                )
                self.files_queued += 1
                return True
            else:
                logger.warning(
                    f"✗ Skipped detection for {file_analysis.file_name}: Job already exists"
                )
                return False

        except Exception as e:
            logger.error(f"Error queuing language detection job: {e}")
            return False

    def _check_and_queue_transcription_for_file(self, file_path: str, detected_lang_code: str):
        """
        Check if a file with detected language matches any scan rules and queue transcription.

        Args:
            file_path: Path to the file
            detected_lang_code: Detected language code (ISO 639-1, e.g., 'ja', 'en')
        """
        try:
            logger.info(
                f"Checking if {file_path} with language '{detected_lang_code}' "
                f"matches any scan rules..."
            )

            # Load scan rules
            rules = self._load_scan_rules()
            if not rules:
                logger.debug("No active scan rules found")
                return

            # Check each rule
            for rule in rules:
                # Check if language matches
                if rule.audio_language_is:
                    try:
                        rule_lang = LanguageCode.from_string(rule.audio_language_is)
                        # Convert detected language (ISO 639-1) to LanguageCode for comparison
                        detected_lang = LanguageCode.from_iso_639_1(detected_lang_code)

                        if detected_lang != rule_lang:
                            logger.debug(
                                f"Rule '{rule.name}' requires language {rule_lang}, "
                                f"but detected {detected_lang}"
                            )
                            continue
                    except Exception as e:
                        logger.warning(f"Could not parse rule language code: {e}")
                        continue

                # Check if language should be excluded
                if rule.audio_language_not:
                    excluded_langs = [
                        LanguageCode.from_string(lang.strip())
                        for lang in rule.audio_language_not.split(',')
                    ]
                    detected_lang_obj = LanguageCode.from_iso_639_1(detected_lang_code)
                    if detected_lang_obj in excluded_langs:
                        logger.debug(
                            f"Rule '{rule.name}' excludes language {detected_lang_code}"
                        )
                        continue

                # File matches this rule - queue transcription job
                logger.info(
                    f"File {file_path} matches rule '{rule.name}' - queueing transcription job"
                )

                # Get target language (use ISO 639-1 throughout)
                target_lang_code = rule.target_language or "eng"

                # Map quality preset
                quality_map = {
                    "fast": QualityPreset.FAST,
                    "balanced": QualityPreset.BALANCED,
                    "best": QualityPreset.BEST,
                }
                quality = quality_map.get(rule.quality_preset, QualityPreset.FAST)

                # Create transcription job
                # All language codes in ISO 639-1 format (ja, en, es)
                job = queue_manager.add_job(
                    file_path=file_path,
                    file_name=os.path.basename(file_path),
                    source_lang=detected_lang_code,  # ISO 639-1 (ja, en, es)
                    target_lang=target_lang_code,    # ISO 639-1 (es, en, fr, etc)
                    quality_preset=quality,
                    transcribe_or_translate=rule.action_type or "translate",
                    priority=rule.job_priority or 5,
                    is_manual_request=False,
                )

                if job:
                    logger.info(
                        f"✓ Queued transcription job {job.id} for {os.path.basename(file_path)}: "
                        f"{rule.action_type} {detected_lang_code} → {target_lang_code}"
                    )
                    self.files_queued += 1

                # Only queue once (first matching rule)
                return

            logger.debug(f"File {file_path} does not match any scan rules")

        except Exception as e:
            logger.error(
                f"Error checking scan rules for {file_path}: {e}",
                exc_info=True
            )

    def _queue_job_from_rule(
        self, file_analysis: FileAnalysis, rule: ScanRule
    ) -> bool:
        """
        Create and queue a job based on matched rule.

        Args:
            file_analysis: File analysis
            rule: Matched scan rule

        Returns:
            True if job was queued successfully
        """
        try:
            # Map quality preset
            quality_map = {
                "fast": QualityPreset.FAST,
                "balanced": QualityPreset.BALANCED,
                "best": QualityPreset.BEST,
            }
            quality_preset = quality_map.get(rule.quality_preset, QualityPreset.FAST)

            # Determine source language (default audio track)
            source_lang = file_analysis.default_audio_language
            source_lang_code = source_lang.to_iso_639_1() if source_lang else None

            # Add job to queue
            job = queue_manager.add_job(
                file_path=file_analysis.file_path,
                file_name=file_analysis.file_name,
                source_lang=source_lang_code,
                target_lang=rule.target_language,
                quality_preset=quality_preset,
                priority=rule.job_priority,
                transcribe_or_translate=rule.action_type,
            )

            if job:
                logger.info(
                    f"✓ Queued job {job.id} for {file_analysis.file_name}: "
                    f"{rule.action_type} {source_lang_code} → {rule.target_language}"
                )
                self.files_queued += 1
                return True
            else:
                logger.warning(
                    f"✗ Skipped {file_analysis.file_name}: Job already exists or in queue "
                    f"(path: {file_analysis.file_path}, target: {rule.target_language})"
                )
                return False

        except Exception as e:
            logger.error(f"Error queuing job: {e}")
            return False

    def _load_scan_rules(self) -> List[ScanRule]:
        """
        Load enabled scan rules from database.

        Returns:
            List of enabled rules (sorted by priority)
        """
        with database.get_session() as session:
            rules = (
                session.query(ScanRule)
                .filter(ScanRule.enabled == True)
                .order_by(ScanRule.priority.desc(), ScanRule.id)
                .all()
            )
            # Expunge rules from session so they can be used outside the context
            for rule in rules:
                session.expunge(rule)
            return rules

    def _persist_scan_stats(self, files_in_this_scan: int = 0):
        """
        Persist scan statistics to database for persistence across restarts.

        Args:
            files_in_this_scan: Number of files scanned in the current scan operation
        """
        from backend.core.settings_service import settings_service

        try:
            # Save last scan time
            if self.last_scan_time:
                settings_service.set(
                    'scanner_last_scan_time',
                    self.last_scan_time.isoformat(),
                    category='scanner'
                )

            # Increment scan count
            scan_count = settings_service.get('scanner_scan_count', 0)
            try:
                scan_count = int(scan_count)
            except (ValueError, TypeError):
                scan_count = 0

            scan_count += 1
            settings_service.set(
                'scanner_scan_count',
                str(scan_count),
                category='scanner'
            )

            # Save total files scanned (cumulative)
            if files_in_this_scan > 0:
                current_total = settings_service.get('scanner_total_files_scanned', 0)
                try:
                    current_total = int(current_total)
                except (ValueError, TypeError):
                    current_total = 0

                new_total = current_total + files_in_this_scan
                settings_service.set(
                    'scanner_total_files_scanned',
                    str(new_total),
                    category='scanner'
                )

                logger.debug(f"Persisted scan stats: scan_count={scan_count}, last_scan={self.last_scan_time}, total_files={new_total}")
            else:
                logger.debug(f"Persisted scan stats: scan_count={scan_count}, last_scan={self.last_scan_time}")
        except Exception as e:
            logger.error(f"Failed to persist scan stats: {e}")

    # === Scheduler Methods ===

    def start_scheduler(self, interval_minutes: Optional[int] = None):
        """
        Start scheduled periodic scanning.

        Args:
            interval_minutes: Scan interval (uses config if None)
        """
        if self.scheduler and self.scheduler.running:
            logger.warning("Scheduler already running")
            return

        from backend.core.settings_service import settings_service
        interval = interval_minutes or int(settings_service.get('scanner_schedule_interval_minutes', 360))

        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            func=self.scan_libraries,
            trigger="interval",
            minutes=interval,
            id="library_scan",
            name=f"Library scan (every {interval}m)",
        )
        self.scheduler.start()

        logger.info(f"Scheduler started: scanning every {interval} minutes")

    def stop_scheduler(self):
        """Stop scheduled scanning."""
        if self.scheduler and self.scheduler.running:
            try:
                # wait=False to avoid blocking on running jobs
                self.scheduler.shutdown(wait=False)
            except Exception as e:
                logger.warning(f"Error shutting down scheduler: {e}")
            self.scheduler = None
            logger.info("Scheduler stopped")

    # === File Watcher Methods ===

    def start_file_watcher(self, paths: Optional[List[str]] = None, recursive: bool = True):
        """
        Start real-time file watching.

        Args:
            paths: Paths to watch (uses config if None)
            recursive: Whether to watch subdirectories
        """
        if self.file_observer:
            logger.warning("File watcher already running")
            return

        # Get paths from settings_service if not provided
        if paths is None:
            from backend.core.settings_service import settings_service
            library_paths = settings_service.get('library_paths', '')
            if not library_paths:
                logger.error("No library paths configured")
                return
            # Handle both comma and pipe separators
            if '|' in library_paths:
                paths = [p.strip() for p in library_paths.split("|") if p.strip()]
            else:
                paths = [p.strip() for p in library_paths.split(",") if p.strip()]

        self.file_observer = Observer()
        handler = LibraryFileHandler(self)

        for path in paths:
            if os.path.isdir(path):
                self.file_observer.schedule(handler, path, recursive=recursive)
                logger.info(f"Watching: {path} (recursive={recursive})")

        self.file_observer.start()
        logger.info("File watcher started")

    def stop_file_watcher(self):
        """Stop real-time file watching."""
        if self.file_observer:
            try:
                self.file_observer.stop()
                # Use timeout to avoid blocking indefinitely
                self.file_observer.join(timeout=5.0)
            except Exception as e:
                logger.warning(f"Error stopping file watcher: {e}")
            self.file_observer = None
            logger.info("File watcher stopped")

    def get_status(self) -> Dict:
        """
        Get scanner status.

        Returns:
            Dictionary with scanner status
        """
        from backend.core.settings_service import settings_service

        watched_paths = []
        if self.file_observer:
            # Get watched paths from observer
            watched_paths = [str(w.path) for w in self.file_observer.emitters]

        next_scan_time = None
        if self.scheduler and self.scheduler.running:
            # Get next scheduled job time
            jobs = self.scheduler.get_jobs()
            if jobs:
                next_scan_time = jobs[0].next_run_time.isoformat()

        # Get last_scan_time from database (persisted) or memory (current session)
        last_scan_time = self.last_scan_time
        if last_scan_time is None:
            # Try to load from database
            db_last_scan = settings_service.get('scanner_last_scan_time')
            if db_last_scan:
                try:
                    last_scan_time = datetime.fromisoformat(db_last_scan)
                except ValueError:
                    last_scan_time = None

        # Get scan count from database
        scan_count = settings_service.get('scanner_scan_count', 0)
        try:
            scan_count = int(scan_count)
        except (ValueError, TypeError):
            scan_count = 0

        # Get total_files_scanned from database
        total_files_scanned = settings_service.get('scanner_total_files_scanned', 0)
        try:
            total_files_scanned = int(total_files_scanned)
        except (ValueError, TypeError):
            total_files_scanned = 0

        return {
            "scheduler_enabled": self.scheduler is not None,
            "scheduler_running": self.scheduler is not None and self.scheduler.running,
            "next_scan_time": next_scan_time,
            "watcher_enabled": self.file_observer is not None,
            "watcher_running": self.file_observer is not None,
            "watched_paths": watched_paths,
            "last_scan_time": last_scan_time.isoformat() if last_scan_time else None,
            "total_scans": scan_count,
            "total_files_scanned": total_files_scanned,
        }

    def scan_paths(self, paths: List[str], recursive: bool = True) -> Dict:
        """
        Scan specific paths.

        Args:
            paths: List of paths to scan
            recursive: Whether to scan subdirectories

        Returns:
            Scan result dictionary
        """
        if self.is_scanning:
            logger.warning("Scan already in progress")
            return {
                "scanned_files": 0,
                "matched_files": 0,
                "jobs_created": 0,
                "skipped_files": 0,
                "paths_scanned": [],
                "error": "Scan already in progress"
            }

        self.is_scanning = True
        scanned = 0
        matched = 0
        jobs_created = 0
        skipped = 0

        try:

            for path in paths:
                if not os.path.exists(path):
                    logger.warning(f"Path does not exist: {path}")
                    continue

                # Scan directory
                if os.path.isdir(path):
                    for root, dirs, files in os.walk(path):
                        for file in files:
                            file_path = os.path.join(root, file)

                            if not FileAnalyzer.is_video_file(file_path):
                                continue

                            scanned += 1

                            # Process file
                            if self.process_file(file_path):
                                matched += 1
                                jobs_created += 1
                            else:
                                skipped += 1

                        if not recursive:
                            break

                # Single file
                elif os.path.isfile(path):
                    if FileAnalyzer.is_video_file(path):
                        scanned += 1
                        if self.process_file(path):
                            matched += 1
                            jobs_created += 1
                        else:
                            skipped += 1

            self.last_scan_time = datetime.now(timezone.utc)
            self.files_scanned += scanned
            self._persist_scan_stats(files_in_this_scan=scanned)

            return {
                "scanned_files": scanned,
                "matched_files": matched,
                "jobs_created": jobs_created,
                "skipped_files": skipped,
                "paths_scanned": paths,
            }

        finally:
            self.is_scanning = False


# Global scanner instance
library_scanner = LibraryScanner()
