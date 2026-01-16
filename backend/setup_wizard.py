"""Setup wizard for first-time configuration."""
import os
import sys
import socket
from pathlib import Path
from typing import Optional, List, Dict


class SetupWizard:
    """Interactive setup wizard for first run."""

    def __init__(self):
        """Initialize setup wizard."""
        self.config_file = Path(".env")

    def is_first_run(self) -> bool:
        """
        Check if this is the first run.

        Returns:
            True if first run (setup_completed setting is not true)
        """
        try:
            from backend.core.settings_service import settings_service
            setup_completed = settings_service.get("setup_completed", None)
            return setup_completed != "true"
        except Exception:
            # Database not initialized yet, assume first run
            return True

    def run(self) -> bool:
        """
        Run the setup wizard.

        Returns:
            True if setup completed successfully
        """
        print("\n" + "=" * 70)
        print("  🎬 TranscriptorIO - First Run Setup Wizard")
        print("=" * 70 + "\n")

        # Step 1: Select mode
        mode = self._select_mode()
        if not mode:
            return False

        # Step 2: Configure based on mode
        if mode == "standalone":
            config = self._configure_standalone_mode()
        else:  # bazarr
            config = self._configure_bazarr_mode()

        if not config:
            return False

        # Step 3: Save configuration to database
        return self._save_to_database(config)

    def _select_mode(self) -> Optional[str]:
        """
        Prompt user to select operation mode.

        Returns:
            'standalone' or 'bazarr', or None if cancelled
        """
        print("Select operation mode:\n")
        print("  1. Standalone Mode")
        print("     - Automatic library scanning")
        print("     - Rule-based subtitle generation")
        print("     - Scheduled/real-time file watching")
        print()
        print("  2. Bazarr Slave Mode")
        print("     - Receives tasks from Bazarr")
        print("     - Custom provider integration")
        print("     - On-demand transcription only")
        print()

        while True:
            choice = input("Enter mode (1 or 2): ").strip()

            if choice == "1":
                return "standalone"
            elif choice == "2":
                return "bazarr"
            elif choice.lower() in ["q", "quit", "exit"]:
                print("\nSetup cancelled.")
                return None
            else:
                print("Invalid choice. Please enter 1 or 2 (or 'q' to quit).\n")

    def _configure_standalone_mode(self) -> Optional[dict]:
        """
        Configure standalone mode settings.

        Returns:
            Configuration dict or None if cancelled
        """
        print("\n" + "-" * 70)
        print("  📁 Standalone Mode Configuration")
        print("-" * 70 + "\n")

        config = {
            "transcriptarr_mode": "standalone",
            "scanner_enabled": True,
            "scanner_schedule_enabled": True,
            "scanner_file_watcher_enabled": False,
            "bazarr_provider_enabled": False,
        }

        # Step 1: Library paths
        print("Step 1: Library Paths")
        print("-" * 40)
        library_paths = self._configure_library_paths()
        if not library_paths:
            return None
        config["library_paths"] = library_paths

        # Step 2: Scanner settings
        print("\nStep 2: Scanner Configuration")
        print("-" * 40)
        scanner_config = self._configure_scanner()
        config.update(scanner_config)

        # Step 3: Worker configuration
        print("\nStep 3: Worker Configuration")
        print("-" * 40)
        worker_config = self._configure_workers()
        config.update(worker_config)

        # Step 4: Scan rules (at least one)
        print("\nStep 4: Scan Rules")
        print("-" * 40)
        print("You need at least one scan rule to determine which files to process.\n")

        rules = []
        while True:
            rule = self._create_scan_rule(len(rules) + 1)
            if rule:
                rules.append(rule)
                print(f"\n✅ Rule {len(rules)} created successfully!\n")

                if len(rules) >= 1:
                    add_more = input("Add another rule? (y/n) [n]: ").strip().lower()
                    if add_more != "y":
                        break
            else:
                if len(rules) == 0:
                    print("\n⚠️  You need at least one rule. Let's try again.\n")
                else:
                    break

        config["scan_rules"] = rules

        return config

    def _configure_library_paths(self) -> Optional[List[str]]:
        """
        Configure library paths to scan.

        Returns:
            List of paths or None if cancelled
        """
        print("Enter the folders where your media files are stored.")
        print("You can add multiple paths (one per line). Enter empty line when done.\n")
        print("Examples:")
        print("  /media/anime")
        print("  /mnt/movies")
        print("  /data/series\n")

        paths = []
        while True:
            if len(paths) == 0:
                prompt = "Enter first path: "
            else:
                prompt = f"Enter path {len(paths) + 1} (or press Enter to finish): "

            path = input(prompt).strip()

            # Empty input
            if not path:
                if len(paths) == 0:
                    print("❌ You need at least one path.\n")
                    continue
                else:
                    break

            # Validate path
            if not os.path.isabs(path):
                print("❌ Path must be absolute (start with /).\n")
                continue

            if not os.path.isdir(path):
                print(f"⚠️  Warning: Path '{path}' does not exist.")
                confirm = input("Add it anyway? (y/n): ").strip().lower()
                if confirm != "y":
                    continue

            paths.append(path)
            print(f"✅ Added: {path}\n")

        print(f"\n📁 Total paths configured: {len(paths)}")
        for i, p in enumerate(paths, 1):
            print(f"   {i}. {p}")

        return paths

    def _configure_scanner(self) -> dict:
        """
        Configure scanner settings.

        Returns:
            Scanner configuration dict
        """
        config = {}

        # Scheduled scanning
        print("\n🕒 Scheduled Scanning")
        print("Scan your library periodically (e.g., every 60 minutes).\n")
        enable_schedule = input("Enable scheduled scanning? (y/n) [y]: ").strip().lower()
        config["scanner_schedule_enabled"] = enable_schedule != "n"

        if config["scanner_schedule_enabled"]:
            while True:
                interval = input("Scan interval in minutes [60]: ").strip()
                if not interval:
                    interval = "60"
                try:
                    interval_int = int(interval)
                    if interval_int < 1:
                        print("❌ Interval must be at least 1 minute.\n")
                        continue
                    config["scanner_schedule_interval_minutes"] = interval_int
                    break
                except ValueError:
                    print("❌ Please enter a valid number.\n")

        # File watcher
        print("\n👁️  Real-time File Watching")
        print("Detect new files immediately as they are added (more CPU intensive).\n")
        enable_watcher = input("Enable real-time file watching? (y/n) [n]: ").strip().lower()
        config["scanner_file_watcher_enabled"] = enable_watcher == "y"

        return config

    def _configure_workers(self) -> dict:
        """
        Configure worker auto-start settings.

        Returns:
            Worker configuration dict
        """
        config = {}

        print("\n⚙️  Worker Auto-Start Configuration")
        print("Workers process transcription jobs. Configure how many should start automatically.\n")

        # Check if Whisper is available
        try:
            from backend.transcription.transcriber import WHISPER_AVAILABLE
            if not WHISPER_AVAILABLE:
                print("⚠️  WARNING: Whisper is not installed!")
                print("   Workers will not start until you install stable-ts or faster-whisper.")
                print("   You can configure workers now and install Whisper later.\n")
        except ImportError:
            print("⚠️  WARNING: Could not check Whisper availability.\n")

        # CPU workers
        print("🖥️  CPU Workers")
        print("CPU workers use your processor. Recommended: 1-2 workers.\n")
        while True:
            cpu_input = input("Number of CPU workers to start on boot [1]: ").strip()
            if not cpu_input:
                cpu_input = "1"
            try:
                cpu_count = int(cpu_input)
                if cpu_count < 0:
                    print("❌ Must be 0 or greater.\n")
                    continue
                config["worker_cpu_count"] = cpu_count
                break
            except ValueError:
                print("❌ Please enter a valid number.\n")

        # GPU workers
        print("\n🎮 GPU Workers")
        print("GPU workers use your graphics card (much faster if available).")
        print("Only configure if you have CUDA-compatible GPU.\n")
        while True:
            gpu_input = input("Number of GPU workers to start on boot [0]: ").strip()
            if not gpu_input:
                gpu_input = "0"
            try:
                gpu_count = int(gpu_input)
                if gpu_count < 0:
                    print("❌ Must be 0 or greater.\n")
                    continue
                config["worker_gpu_count"] = gpu_count
                break
            except ValueError:
                print("❌ Please enter a valid number.\n")

        if config["worker_cpu_count"] == 0 and config["worker_gpu_count"] == 0:
            print("\n⚠️  No workers configured. You can add them later in Settings.")
        else:
            total = config["worker_cpu_count"] + config["worker_gpu_count"]
            print(f"\n✅ Configured {total} worker(s) to start automatically:")
            if config["worker_cpu_count"] > 0:
                print(f"   • {config['worker_cpu_count']} CPU worker(s)")
            if config["worker_gpu_count"] > 0:
                print(f"   • {config['worker_gpu_count']} GPU worker(s)")

        return config

    def _create_scan_rule(self, rule_number: int) -> Optional[dict]:
        """
        Create a single scan rule interactively.

        Args:
            rule_number: Rule number for display

        Returns:
            Rule dict or None if cancelled
        """
        print(f"\nCreating Rule #{rule_number}")
        print("=" * 40)

        # Rule name
        name = input(f"Rule name (e.g., 'Japanese anime to Spanish'): ").strip()
        if not name:
            name = f"Rule {rule_number}"

        # Source audio language
        print("\nSource audio language (ISO 639-2 code):")
        print("  jpn = Japanese")
        print("  eng = English")
        print("  ron = Romanian")
        print("  spa = Spanish")
        print("  (or leave empty for any language)")
        audio_lang = input("Audio language [any]: ").strip().lower() or None

        # Task type
        print("\nAction type:")
        print("  1. Transcribe (audio → English subtitles)")
        print("  2. Translate (audio → English → target language)")
        print("\n📝 Note:")
        print("   • Transcribe: Always creates English subtitles (.eng.srt)")
        print("   • Translate: Creates English + target language subtitles (.eng.srt + .spa.srt)")
        while True:
            task_choice = input("Choose action (1 or 2) [1]: ").strip()
            if not task_choice or task_choice == "1":
                action_type = "transcribe"
                target_lang = "eng"  # Transcribe always targets English
                print("✓ Target language set to: eng (English)")
                break
            elif task_choice == "2":
                action_type = "translate"
                print("\nTarget subtitle language (ISO 639-2 code):")
                print("Examples: spa (Spanish), fra (French), deu (German), ita (Italian)")
                target_lang = input("Target language: ").strip().lower()
                if not target_lang:
                    print("❌ Target language is required for translate mode.")
                    continue
                if target_lang == "eng":
                    print("⚠️  Note: Target is English. Consider using 'transcribe' instead.")
                print(f"✓ Will create: .eng.srt + .{target_lang}.srt")
                break
            else:
                print("❌ Invalid choice. Please enter 1 or 2.\n")

        # Check for missing subtitles
        print("\nOnly process files that are missing subtitles?")
        check_missing = input("Check for missing subtitle (y/n) [y]: ").strip().lower()
        missing_subtitle_lang = target_lang if check_missing != "n" else None

        # Priority
        print("\nRule priority (higher = evaluated first):")
        while True:
            priority_input = input("Priority [10]: ").strip()
            if not priority_input:
                priority = 10
                break
            try:
                priority = int(priority_input)
                break
            except ValueError:
                print("❌ Please enter a valid number.\n")

        rule = {
            "name": name,
            "enabled": True,
            "priority": priority,
            "audio_language_is": audio_lang,
            "missing_external_subtitle_lang": missing_subtitle_lang,
            "action_type": action_type,
            "target_language": target_lang,
            "quality_preset": "fast",
            "job_priority": 0,
        }

        # Show summary
        print("\n📋 Rule Summary:")
        print(f"   Name: {name}")
        print(f"   Audio: {audio_lang or 'any'}")
        print(f"   Action: {action_type}")
        if action_type == "transcribe":
            print(f"   Output: .eng.srt (English subtitles)")
        else:
            print(f"   Output: .eng.srt + .{target_lang}.srt")
        print(f"   Check missing: {'yes' if missing_subtitle_lang else 'no'}")
        print(f"   Priority: {priority}")

        return rule

    def _configure_bazarr_mode(self) -> Optional[dict]:
        """
        Configure Bazarr slave mode settings.

        Returns:
            Configuration dict or None if cancelled
        """
        print("\n" + "-" * 70)
        print("  🔌 Bazarr Slave Mode Configuration")
        print("-" * 70 + "\n")

        config = {
            "transcriptarr_mode": "bazarr",
            "scanner_enabled": False,
            "scanner_schedule_enabled": False,
            "scanner_file_watcher_enabled": False,
            "bazarr_provider_enabled": True,
        }

        # Get network info
        hostname = socket.gethostname()

        # Try to get local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except Exception:
            local_ip = "127.0.0.1"

        print("Bazarr will send transcription requests to this service.\n")
        print("📡 Connection Information:")
        print("=" * 70)
        print(f"\n  Hostname: {hostname}")
        print(f"  Local IP: {local_ip}")
        print(f"  Port: 8000 (default)\n")

        print("Configure Bazarr custom provider with these URLs:")
        print("-" * 70)
        print(f"\n  Localhost (same machine):")
        print(f"    http://localhost:8000/asr")
        print(f"    http://127.0.0.1:8000/asr\n")

        print(f"  Local Network (other machines):")
        print(f"    http://{local_ip}:8000/asr\n")

        print("=" * 70)
        print("\nPress Enter to continue...")
        input()

        return config

    def _save_to_database(self, config: dict) -> bool:
        """
        Save configuration to database instead of .env.

        Args:
            config: Configuration dictionary

        Returns:
            True if saved successfully
        """
        print("\n" + "-" * 70)
        print("  💾 Saving Configuration")
        print("-" * 70 + "\n")

        try:
            # Import here to avoid circular imports
            from backend.core.database import database
            from backend.core.settings_service import settings_service

            # Initialize database if needed
            print("Initializing database...")
            database.init_db()

            # Initialize default settings
            print("Initializing settings...")
            settings_service.init_default_settings()

            # Extract scan rules if present
            scan_rules = config.pop("scan_rules", [])

            # Update settings in database
            settings_dict = {}
            for key, value in config.items():
                # Convert library_paths list to JSON string if needed
                if key == "library_paths" and isinstance(value, list):
                    import json
                    value = json.dumps(value)
                # Convert integers to strings (settings are stored as strings)
                elif isinstance(value, int):
                    value = str(value)
                # Convert booleans to strings
                elif isinstance(value, bool):
                    value = str(value).lower()
                settings_dict[key] = value

            print(f"Saving {len(settings_dict)} settings...")
            settings_service.update_multiple(settings_dict)

            # Create scan rules if in standalone mode
            if scan_rules:
                from backend.core.database import get_session
                from backend.scanning.models import ScanRule

                print(f"Creating {len(scan_rules)} scan rules...")
                with get_session() as session:
                    for rule_data in scan_rules:
                        rule = ScanRule(**rule_data)
                        session.add(rule)
                    session.commit()

            print("\n✅ Configuration saved successfully!")
            print("\n" + "=" * 70)
            print("  🚀 Setup Complete!")
            print("=" * 70)
            print("\nYou can now start the server with:")
            print("  python backend/cli.py server\n")
            print("Or with auto-reload for development:")
            print("  python backend/cli.py server --reload\n")

            if config.get("transcriptarr_mode") == "standalone":
                print("Access the Web UI at:")
                print("  http://localhost:8000\n")

            return True

        except Exception as e:
            print(f"\n❌ Error saving configuration: {e}")
            import traceback
            traceback.print_exc()
            return False


def run_setup_wizard() -> bool:
    """
    Run setup wizard if needed.

    Returns:
        True if setup completed or not needed
    """
    wizard = SetupWizard()

    if not wizard.is_first_run():
        return True

    print("\n⚠️  First run detected - configuration needed\n")

    return wizard.run()


if __name__ == "__main__":
    success = run_setup_wizard()
    sys.exit(0 if success else 1)
