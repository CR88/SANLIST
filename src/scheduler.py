"""
Scheduler for automated daily updates of UK Sanctions List
"""
import logging
import schedule
import time
from datetime import datetime
from typing import Optional

from .config import Config
from .downloader import SanctionsDownloader
from .parser import SanctionsParser
from .database import SanctionsDatabase

logger = logging.getLogger(__name__)


class SanctionsScheduler:
    """
    Manages scheduled updates of sanctions data
    """

    def __init__(self):
        self.config = Config
        self.downloader = SanctionsDownloader(download_dir=self.config.DATA_DIR)
        self.database = SanctionsDatabase(self.config.DATABASE_URL)

    def update_sanctions_data(self) -> bool:
        """
        Complete update workflow: download -> parse -> update database

        Returns:
            bool: True if successful, False otherwise
        """
        start_time = datetime.now()
        logger.info(f"Starting sanctions data update at {start_time}")

        try:
            # Step 1: Download latest XML
            logger.info("Step 1: Downloading latest sanctions list XML...")
            filepath, xml_url = self.downloader.download_latest()

            if not filepath:
                logger.error("Failed to download XML file")
                return False

            logger.info(f"Downloaded XML from: {xml_url}")

            # Step 2: Parse XML
            logger.info("Step 2: Parsing XML file...")
            parser = SanctionsParser(filepath)

            if not parser.load_xml():
                logger.error("Failed to load XML file")
                return False

            entities = parser.parse_entities()

            if not entities:
                logger.error("No entities found in XML")
                return False

            logger.info(f"Parsed {len(entities)} entities from XML")

            # Step 3: Update database
            logger.info("Step 3: Updating database...")
            added, updated, removed, errors = self.database.bulk_upsert(entities)

            logger.info(f"Database update complete:")
            logger.info(f"  - Added: {added}")
            logger.info(f"  - Updated: {updated}")
            logger.info(f"  - Removed: {removed}")
            logger.info(f"  - Errors: {errors}")

            # Step 4: Get stats
            stats = self.database.get_stats()
            logger.info(f"Database statistics:")
            logger.info(f"  - Total entities: {stats['total_entities']}")
            logger.info(f"  - Individuals: {stats['individuals']}")
            logger.info(f"  - Organizations: {stats['organizations']}")
            logger.info(f"  - Total aliases: {stats['total_aliases']}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Update completed successfully in {duration:.2f} seconds")

            return True

        except Exception as e:
            logger.error(f"Error during update: {e}", exc_info=True)
            return False

    def run_once(self):
        """
        Run update once (for testing or manual execution)
        """
        logger.info("Running one-time update")
        success = self.update_sanctions_data()

        if success:
            print("✓ Update completed successfully")
        else:
            print("✗ Update failed - check logs for details")

        return success

    def setup_schedule(self):
        """
        Set up the daily update schedule
        """
        schedule_time = f"{self.config.UPDATE_SCHEDULE_HOUR:02d}:{self.config.UPDATE_SCHEDULE_MINUTE:02d}"
        logger.info(f"Setting up daily update at {schedule_time} {self.config.TIMEZONE}")

        schedule.every().day.at(schedule_time).do(self.update_sanctions_data)

        print(f"✓ Scheduler configured for daily updates at {schedule_time} {self.config.TIMEZONE}")

    def run_scheduler(self):
        """
        Run the scheduler (blocking, runs indefinitely)
        """
        self.setup_schedule()

        logger.info("Scheduler started - running indefinitely")
        print("Scheduler started. Press Ctrl+C to stop.")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            print("\nScheduler stopped")


def setup_logging():
    """
    Configure logging for the scheduler
    """
    import os

    # Create logs directory if it doesn't exist
    os.makedirs(Config.LOG_DIR, exist_ok=True)

    # Configure logging
    log_file = os.path.join(Config.LOG_DIR, 'sanctions_scheduler.log')

    logging.basicConfig(
        level=getattr(logging, Config.LOG_LEVEL),
        format=Config.LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    logger.info("Logging configured")


def main():
    """
    Main entry point for the scheduler
    """
    import argparse

    parser = argparse.ArgumentParser(description='UK Sanctions List Scheduler')
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run update once and exit (instead of scheduling)'
    )
    parser.add_argument(
        '--init-db',
        action='store_true',
        help='Initialize database tables (run once before first use)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    # Print configuration
    Config.print_config()

    scheduler = SanctionsScheduler()

    if args.init_db:
        logger.info("Initializing database...")
        print("Initializing database tables...")
        scheduler.database.create_tables()
        print("✓ Database initialized successfully")
        return

    if args.once:
        # Run once
        scheduler.run_once()
    else:
        # Run scheduler indefinitely
        scheduler.run_scheduler()


if __name__ == "__main__":
    main()
