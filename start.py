#!/usr/bin/env python3
"""
Railway startup script
Initializes database, starts scheduler, and starts the API server
"""
import os
import sys
import logging
import threading
from src.config import Config
from src.database import SanctionsDatabase
from src.scheduler import SanctionsScheduler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize database tables if they don't exist"""
    try:
        logger.info("Checking database initialization...")
        db = SanctionsDatabase(Config.DATABASE_URL)

        # Create tables (will skip if already exist)
        db.create_tables()
        logger.info("✓ Database tables ready")

        # Check if database is empty
        stats = db.get_stats()
        if stats['total_entities'] == 0:
            logger.info("Database is empty. Run initial data update with:")
            logger.info("  python manage.py update")
            logger.info("Or the scheduler will update automatically at scheduled time")
        else:
            logger.info(f"✓ Database has {stats['total_entities']} entities")

        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def start_scheduler_background():
    """Start the scheduler in a background thread"""
    def run_scheduler():
        try:
            logger.info("Starting background scheduler for daily updates...")
            logger.info(f"Scheduled update time: {Config.UPDATE_SCHEDULE_HOUR:02d}:{Config.UPDATE_SCHEDULE_MINUTE:02d} {Config.TIMEZONE}")
            scheduler = SanctionsScheduler()
            scheduler.run_scheduler()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")

    # Start scheduler in daemon thread (won't block main thread)
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("✓ Background scheduler started")


def start_api_server():
    """Start the FastAPI server"""
    try:
        import uvicorn
        from src.api import app

        host = Config.API_HOST
        port = Config.API_PORT

        logger.info(f"Starting API server on {host}:{port}")
        logger.info(f"API documentation: http://{host}:{port}/docs")
        logger.info(f"Web interface: http://{host}:{port}/static/index.html")

        # Start server
        uvicorn.run(
            "src.api:app",
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("UK Sanctions List Bot - Railway Startup")
    logger.info("=" * 60)

    # Initialize database
    if not initialize_database():
        logger.error("Failed to initialize database. Exiting.")
        sys.exit(1)

    # Start scheduler in background thread
    start_scheduler_background()

    # Start API server (this blocks)
    start_api_server()
