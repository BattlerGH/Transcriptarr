"""Database configuration and session management."""
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event, Engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool

from backend.config import settings, DatabaseType

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()


class Database:
    """Database manager supporting SQLite, PostgreSQL, and MariaDB."""

    def __init__(self, auto_create_tables: bool = True):
        """
        Initialize database engine and session maker.

        Args:
            auto_create_tables: If True, automatically create tables if they don't exist
        """
        self.engine = self._create_engine()
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        logger.info(f"Database initialized: {settings.database_type.value}")

        # Automatically create tables if they don't exist
        if auto_create_tables:
            self._ensure_tables_exist()

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine based on database type."""
        connect_args = {}
        poolclass = QueuePool

        if settings.database_type == DatabaseType.SQLITE:
            # SQLite-specific configuration
            connect_args = {
                "check_same_thread": False,  # Allow multi-threaded access
                "timeout": 30.0,  # Wait up to 30s for lock
            }
            # Use StaticPool for SQLite to avoid connection issues
            poolclass = StaticPool

            # Enable WAL mode for better concurrency
            engine = create_engine(
                settings.database_url,
                connect_args=connect_args,
                poolclass=poolclass,
                echo=settings.debug,
            )

            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                """Enable SQLite optimizations."""
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                cursor.close()

        elif settings.database_type == DatabaseType.POSTGRESQL:
            # PostgreSQL-specific configuration
            try:
                import psycopg2  # noqa: F401
            except ImportError:
                raise ImportError(
                    "PostgreSQL support requires psycopg2-binary.\n"
                    "Install it with: pip install psycopg2-binary"
                )

            engine = create_engine(
                settings.database_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before using
                echo=settings.debug,
            )

        elif settings.database_type in (DatabaseType.MARIADB, DatabaseType.MYSQL):
            # MariaDB/MySQL-specific configuration
            try:
                import pymysql  # noqa: F401
            except ImportError:
                raise ImportError(
                    "MariaDB/MySQL support requires pymysql.\n"
                    "Install it with: pip install pymysql"
                )

            connect_args = {
                "charset": "utf8mb4",
            }
            engine = create_engine(
                settings.database_url,
                connect_args=connect_args,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=settings.debug,
            )

        else:
            raise ValueError(f"Unsupported database type: {settings.database_type}")

        return engine

    def _ensure_tables_exist(self):
        """Check if tables exist and create them if they don't."""
        # Import models to register them with Base.metadata
        from backend.core import models  # noqa: F401
        from sqlalchemy import inspect

        inspector = inspect(self.engine)
        existing_tables = inspector.get_table_names()

        # Check if the main 'jobs' table exists
        if 'jobs' not in existing_tables:
            logger.info("Tables don't exist, creating them automatically...")
            self.create_tables()
        else:
            logger.debug("Database tables already exist")

    def create_tables(self):
        """Create all database tables."""
        # Import models to register them with Base.metadata
        from backend.core import models  # noqa: F401

        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=self.engine, checkfirst=True)

        # Verify tables were actually created
        from sqlalchemy import inspect
        inspector = inspect(self.engine)
        created_tables = inspector.get_table_names()

        if 'jobs' in created_tables:
            logger.info(f"Database tables created successfully: {created_tables}")
        else:
            logger.error(f"Failed to create tables. Existing tables: {created_tables}")
            raise RuntimeError("Failed to create database tables")

    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=self.engine)
        logger.info("Database tables dropped")

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session as a context manager.

        Usage:
            with db.get_session() as session:
                session.query(Job).all()
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    def get_db(self) -> Generator[Session, None, None]:
        """
        Dependency for FastAPI endpoints.

        Usage:
            @app.get("/jobs")
            def get_jobs(db: Session = Depends(database.get_db)):
                return db.query(Job).all()
        """
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            from sqlalchemy import text
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def get_stats(self) -> dict:
        """Get database statistics."""
        stats = {
            "type": settings.database_type.value,
            "url": settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
            "pool_size": getattr(self.engine.pool, "size", lambda: "N/A")(),
            "pool_checked_in": getattr(self.engine.pool, "checkedin", lambda: 0)(),
            "pool_checked_out": getattr(self.engine.pool, "checkedout", lambda: 0)(),
            "pool_overflow": getattr(self.engine.pool, "overflow", lambda: 0)(),
        }
        return stats


# Global database instance
database = Database()