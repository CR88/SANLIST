#!/usr/bin/env python3
"""
Railway startup script
Initializes database, starts scheduler, and starts the API server
"""
import os
import sys
import logging
import threading
import schedule
import time
from src.config import Config
from src.database import SanctionsDatabase
from src.scheduler import SanctionsScheduler
from src.ec_scheduler import ECScheduler
from src.ec_database import ECDatabase

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

        # Debug: Check which DATABASE_URL is being used
        db_url_safe = Config.get_database_url(hide_password=True)
        logger.info(f"Using database: {db_url_safe}")

        # Check if DATABASE_URL env var is set
        if not os.getenv('DATABASE_URL') and not os.getenv('PGURL') and not os.getenv('DATABASE_PRIVATE_URL'):
            logger.warning("⚠️ No DATABASE_URL environment variable found!")
            logger.warning("⚠️ Available env vars: " + ", ".join([k for k in os.environ.keys() if 'DATA' in k or 'PG' in k or 'POSTGRES' in k]))

        # Initialize UK Sanctions tables
        sanctions_db = SanctionsDatabase(Config.DATABASE_URL)
        sanctions_db.create_tables()
        logger.info("✓ UK Sanctions tables ready")

        # Initialize Electoral Commission tables
        ec_db = ECDatabase(Config.DATABASE_URL)
        ec_db.create_tables()
        logger.info("✓ Electoral Commission tables ready")

        # Check sanctions database
        sanctions_stats = sanctions_db.get_stats()
        if sanctions_stats['total_entities'] == 0:
            logger.info("Sanctions database is empty. Will update at scheduled time")
        else:
            logger.info(f"✓ Sanctions database has {sanctions_stats['total_entities']} entities")

        # Check EC database
        ec_stats = ec_db.get_stats()
        if ec_stats['total_donations'] == 0:
            logger.info("EC database is empty. Will update at scheduled time")
        else:
            logger.info(f"✓ EC database has {ec_stats['total_donations']:,} donations")

        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def start_scheduler_background():
    """Start the scheduler in a background thread for both UK Sanctions and EC"""
    def run_scheduler():
        try:
            logger.info("Starting background scheduler for daily updates...")
            logger.info(f"Scheduled update time: {Config.UPDATE_SCHEDULE_HOUR:02d}:{Config.UPDATE_SCHEDULE_MINUTE:02d} {Config.TIMEZONE}")

            sanctions_scheduler = SanctionsScheduler()
            ec_scheduler = ECScheduler()

            # Schedule UK Sanctions update (configured time)
            schedule_time = f"{Config.UPDATE_SCHEDULE_HOUR:02d}:{Config.UPDATE_SCHEDULE_MINUTE:02d}"
            schedule.every().day.at(schedule_time).do(sanctions_scheduler.update_sanctions_data)
            logger.info(f"✓ UK Sanctions scheduled for {schedule_time} {Config.TIMEZONE}")

            # Schedule Electoral Commission update (6 hours after sanctions to avoid memory overlap)
            ec_hour = (Config.UPDATE_SCHEDULE_HOUR + 6) % 24
            ec_minute = Config.UPDATE_SCHEDULE_MINUTE
            ec_time = f"{ec_hour:02d}:{ec_minute:02d}"
            schedule.every().day.at(ec_time).do(ec_scheduler.update_ec_data)
            logger.info(f"✓ Electoral Commission scheduled for {ec_time} {Config.TIMEZONE}")

            # Run scheduler loop
            logger.info("✓ Background scheduler running")
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except Exception as e:
            logger.error(f"Scheduler error: {e}")

    # Start scheduler in daemon thread (won't block main thread)
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    logger.info("✓ Background scheduler thread started")


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
    logger.info("UK Sanctions + Electoral Commission Bot - Railway Startup")
    logger.info("=" * 60)

    # Initialize database
    if not initialize_database():
        logger.error("Failed to initialize database. Exiting.")
        sys.exit(1)

    # Run one-time update if requested via env var
    if os.getenv('RUN_EC_UPDATE_ON_STARTUP', '').lower() == 'true':
        logger.info("RUN_EC_UPDATE_ON_STARTUP is set - triggering EC update...")
        try:
            ec_scheduler = ECScheduler()
            ec_scheduler.update_ec_data()
            logger.info("Startup EC update complete")
        except Exception as e:
            logger.error(f"Startup EC update failed: {e}")

    # Start scheduler in background thread
    start_scheduler_background()

    # Start API server (this blocks)
    start_api_server()
