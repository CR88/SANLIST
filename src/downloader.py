"""
Downloader module for UK Sanctions List
Scrapes the gov.uk page to find the current XML URL and downloads the file
"""
import os
import logging
from typing import Optional, Tuple
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SanctionsDownloader:
    """
    Downloads UK Sanctions List XML file
    """

    def __init__(self, download_dir: str = "data"):
        self.base_url = "https://www.gov.uk/government/publications/the-uk-sanctions-list"
        self.download_dir = download_dir
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; UKSanctionsBot/1.0)'
        })

        # Create download directory if it doesn't exist
        os.makedirs(self.download_dir, exist_ok=True)

    def get_xml_url(self) -> Optional[str]:
        """
        Scrape the gov.uk page to find the current XML file URL

        Returns:
            str: URL to the XML file, or None if not found
        """
        try:
            logger.info(f"Fetching sanctions list page: {self.base_url}")
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for XML download link
            # The page typically has a link with text containing 'XML' or ending in .xml
            xml_link = None

            # Method 1: Find links containing .xml
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '.xml' in href.lower():
                    # Convert relative URL to absolute if needed
                    if href.startswith('/'):
                        xml_link = f"https://www.gov.uk{href}"
                    elif href.startswith('http'):
                        xml_link = href
                    else:
                        xml_link = f"https://www.gov.uk/{href}"
                    break

            # Method 2: Look for specific attachment sections
            if not xml_link:
                attachment_sections = soup.find_all('div', class_='attachment-details')
                for section in attachment_sections:
                    link = section.find('a', href=True)
                    title = section.get_text().lower()
                    if link and 'xml' in title:
                        href = link['href']
                        if href.startswith('/'):
                            xml_link = f"https://www.gov.uk{href}"
                        elif href.startswith('http'):
                            xml_link = href
                        break

            if xml_link:
                logger.info(f"Found XML URL: {xml_link}")
                return xml_link
            else:
                logger.error("Could not find XML download link on page")
                return None

        except requests.RequestException as e:
            logger.error(f"Error fetching sanctions list page: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while getting XML URL: {e}")
            return None

    def download_xml(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """
        Download XML file from given URL

        Args:
            url: URL to download from
            filename: Optional custom filename (default: auto-generated with timestamp)

        Returns:
            str: Path to downloaded file, or None if download failed
        """
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"uk_sanctions_list_{timestamp}.xml"

            filepath = os.path.join(self.download_dir, filename)

            logger.info(f"Downloading XML from: {url}")
            response = self.session.get(url, timeout=60, stream=True)
            response.raise_for_status()

            # Save file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            file_size = os.path.getsize(filepath)
            logger.info(f"Successfully downloaded XML to: {filepath} ({file_size:,} bytes)")

            return filepath

        except requests.RequestException as e:
            logger.error(f"Error downloading XML file: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error while downloading XML: {e}")
            return None

    def download_latest(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Find and download the latest sanctions list XML file

        Returns:
            Tuple[str, str]: (file_path, xml_url) or (None, None) if failed
        """
        xml_url = self.get_xml_url()
        if not xml_url:
            logger.error("Failed to get XML URL")
            return None, None

        filepath = self.download_xml(xml_url)
        if not filepath:
            logger.error("Failed to download XML file")
            return None, None

        return filepath, xml_url


def main():
    """
    Main function for testing the downloader
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    downloader = SanctionsDownloader()
    filepath, url = downloader.download_latest()

    if filepath:
        print(f"✓ Successfully downloaded: {filepath}")
        print(f"  URL: {url}")
    else:
        print("✗ Download failed")


if __name__ == "__main__":
    main()
