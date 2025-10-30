"""
Electoral Commission CSV downloader
Downloads political donations data from the Electoral Commission website
"""
import os
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ECDownloader:
    """
    Downloads Electoral Commission political donations CSV data
    """

    # Base URL for CSV export - discovered via API endpoint testing
    CSV_EXPORT_URL = "https://search.electoralcommission.org.uk/api/csv/donations"

    def __init__(self, download_dir: str = "data/ec"):
        """
        Initialize downloader

        Args:
            download_dir: Directory to save downloaded CSV files
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download_latest(self, max_rows: int = 999999) -> Tuple[Optional[str], Optional[str]]:
        """
        Download the latest Electoral Commission donations CSV

        Args:
            max_rows: Maximum number of rows to download (default: all)

        Returns:
            Tuple of (filepath, url) or (None, None) if failed
        """
        try:
            # Build the CSV export URL - simplified params that work with the API
            params = {
                'rows': str(max_rows),  # Number of records to fetch
                'sort': 'AcceptedDate',
                'order': 'desc',
            }

            logger.info(f"Downloading Electoral Commission CSV (max {max_rows} rows)...")
            logger.info(f"URL: {self.CSV_EXPORT_URL}")

            # Download CSV
            response = requests.get(self.CSV_EXPORT_URL, params=params, timeout=300)
            response.raise_for_status()

            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"ec_donations_{timestamp}.csv"
            filepath = self.download_dir / filename

            # Save file
            with open(filepath, 'wb') as f:
                f.write(response.content)

            file_size = filepath.stat().st_size
            logger.info(f"Successfully downloaded CSV to: {filepath} ({file_size:,} bytes)")

            return str(filepath), self.CSV_EXPORT_URL

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download Electoral Commission CSV: {e}")
            return None, None
        except Exception as e:
            logger.error(f"Unexpected error downloading CSV: {e}")
            return None, None


def main():
    """
    Test the Electoral Commission downloader
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    downloader = ECDownloader()
    filepath, url = downloader.download_latest()

    if filepath:
        print(f"\n✓ Download successful!")
        print(f"  File: {filepath}")
        print(f"  URL: {url}")
    else:
        print("\n✗ Download failed")


if __name__ == "__main__":
    main()
