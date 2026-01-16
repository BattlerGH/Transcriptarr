#!/usr/bin/env python3
"""CLI entry point for Transcriptarr backend."""
import argparse
import logging
import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import uvicorn


def main():
    """Main CLI entry point."""

    parser = argparse.ArgumentParser(
        description="Transcriptarr - AI-powered subtitle transcription service"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Server command
    server_parser = subparsers.add_parser("server", help="Run FastAPI server")
    server_parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    server_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    server_parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    server_parser.add_argument(
        "--log-level",
        choices=["debug", "info", "warning", "error", "critical"],
        default="info",
        help="Log level (default: info)"
    )

    # Database command
    db_parser = subparsers.add_parser("db", help="Database operations")
    db_parser.add_argument(
        "action",
        choices=["init", "migrate", "reset", "backup"],
        help="Database action"
    )

    # Worker command
    worker_parser = subparsers.add_parser("worker", help="Start standalone worker")
    worker_parser.add_argument(
        "--type",
        choices=["cpu", "gpu"],
        default="cpu",
        help="Worker type (default: cpu)"
    )
    worker_parser.add_argument(
        "--device-id",
        type=int,
        default=0,
        help="GPU device ID (default: 0)"
    )

    # Scanner command
    scan_parser = subparsers.add_parser("scan", help="Run library scan")
    scan_parser.add_argument(
        "paths",
        nargs="+",
        help="Paths to scan"
    )
    scan_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Don't scan subdirectories"
    )

    # Setup command
    subparsers.add_parser("setup", help="Run setup wizard")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Execute command
    if args.command == "server":
        run_server(args)
    elif args.command == "db":
        run_db_command(args)
    elif args.command == "worker":
        run_worker(args)
    elif args.command == "scan":
        run_scan(args)
    elif args.command == "setup":
        run_setup()


def run_server(args):
    """Run FastAPI server."""
    print(f"🚀 Starting Transcriptarr server on {args.host}:{args.port}")
    print(f"📖 API docs available at: http://{args.host}:{args.port}/docs")

    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level=args.log_level,
    )


def run_db_command(args):
    """Run database command."""
    from backend.core.database import database

    if args.action == "init":
        print("Initializing database...")
        database.init_db()
        print("✅ Database initialized")

    elif args.action == "reset":
        print("⚠️  WARNING: This will delete all data!")
        confirm = input("Type 'yes' to confirm: ")

        if confirm.lower() == "yes":
            print("Resetting database...")
            database.reset_db()
            print("✅ Database reset")
        else:
            print("❌ Cancelled")

    elif args.action == "migrate":
        print("❌ Migrations not yet implemented")
        sys.exit(1)

    elif args.action == "backup":
        print("❌ Backup not yet implemented")
        sys.exit(1)


def run_worker(args):
    """Run standalone worker."""
    from backend.core.worker import Worker, WorkerType
    import signal

    worker_type = WorkerType.CPU if args.type == "cpu" else WorkerType.GPU
    device_id = args.device_id if worker_type == WorkerType.GPU else None

    worker_id = f"standalone-{args.type}"
    if device_id is not None:
        worker_id += f"-{device_id}"

    print(f"🔧 Starting standalone worker: {worker_id}")

    worker = Worker(worker_id, worker_type, device_id)

    # Handle shutdown
    def signal_handler(sig, frame):
        print("\n⏹️  Stopping worker...")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    worker.start()

    # Keep alive
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        worker.stop()


def run_scan(args):
    """Run library scan."""
    from backend.scanning.library_scanner import library_scanner

    print(f"🔍 Scanning {len(args.paths)} path(s)...")

    result = library_scanner.scan_paths(
        paths=args.paths,
        recursive=not args.no_recursive
    )

    print(f"\n✅ Scan complete:")
    print(f"   📁 Files scanned: {result['scanned_files']}")
    print(f"   ✅ Matched: {result['matched_files']}")
    print(f"   📋 Jobs created: {result['jobs_created']}")
    print(f"   ⏭️  Skipped: {result['skipped_files']}")


def run_setup():
    """Run setup wizard."""
    from backend.setup_wizard import SetupWizard

    wizard = SetupWizard()
    wizard.run()


if __name__ == "__main__":
    main()

