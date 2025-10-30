"""
Electoral Commission data update scheduler
"""
import logging
from datetime import datetime

from .config import Config
from .ec_downloader import ECDownloader
from .ec_parser import ECParser
from .ec_database import ECDatabase

logger = logging.getLogger(__name__)


class ECScheduler:
    """
    Manages Electoral Commission data updates
    """

    def __init__(self):
        self.config = Config
        self.downloader = ECDownloader()
        self.database = ECDatabase(self.config.DATABASE_URL)

    def update_ec_data(self) -> bool:
        """
        Complete update workflow: download -> parse -> update database

        Returns:
            bool: True if successful, False otherwise
        """
        start_time = datetime.now()
        logger.info(f"Starting EC data update at {start_time}")

        try:
            # Step 1: Download latest CSV
            logger.info("Step 1: Downloading latest Electoral Commission CSV...")
            filepath, csv_url = self.downloader.download_latest()

            if not filepath:
                logger.error("Failed to download CSV file")
                return False

            logger.info(f"Downloaded CSV from: {csv_url}")

            # Step 2: Parse CSV
            logger.info("Step 2: Parsing CSV file...")
            parser = ECParser(filepath)
            donations = parser.parse_donations()

            if not donations:
                logger.error("No donations found in CSV")
                return False

            logger.info(f"Parsed {len(donations)} donations from CSV")

            # Step 3: Update database
            logger.info("Step 3: Updating database...")
            added, updated, errors = self.database.bulk_upsert(donations, filepath)

            logger.info(f"Database update complete:")
            logger.info(f"  - Added: {added}")
            logger.info(f"  - Updated: {updated}")
            logger.info(f"  - Errors: {errors}")

            # Step 4: Get stats
            stats = self.database.get_stats()
            logger.info(f"Database statistics:")
            logger.info(f"  - Total donations: {stats['total_donations']:,}")
            logger.info(f"  - Total value: £{stats['total_value']:,.2f}")
            logger.info(f"  - Unique donors: {stats['unique_donors']:,}")
            logger.info(f"  - Unique recipients: {stats['unique_recipients']:,}")

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Update completed successfully in {duration:.2f} seconds")

            return True

        except Exception as e:
            logger.error(f"Error during update: {e}", exc_info=True)
            return False


def main():
    """
    Test EC scheduler
    """
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    scheduler = ECScheduler()
    success = scheduler.update_ec_data()

    if success:
        print("✓ EC update completed successfully")
    else:
        print("✗ EC update failed")


if __name__ == "__main__":
    main()
