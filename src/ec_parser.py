"""
Electoral Commission CSV parser
Parses political donations CSV data from the Electoral Commission
"""
import csv
import logging
from datetime import datetime
from typing import List, Dict, Optional
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)


class ECParser:
    """
    Parses Electoral Commission donations CSV files
    """

    def __init__(self, csv_path: str):
        """
        Initialize parser

        Args:
            csv_path: Path to the CSV file
        """
        self.csv_path = Path(csv_path)

    def parse_donations(self) -> List[Dict]:
        """
        Parse donations from CSV file

        Returns:
            List of donation dictionaries
        """
        donations = []

        try:
            logger.info(f"Parsing Electoral Commission CSV: {self.csv_path}")

            with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)

                for row_num, row in enumerate(reader, start=1):
                    try:
                        donation = self._parse_row(row)
                        if donation:
                            donations.append(donation)
                    except Exception as e:
                        logger.warning(f"Error parsing row {row_num}: {e}")
                        continue

            logger.info(f"Parsed {len(donations)} donations from CSV")
            return donations

        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            return []

    def _parse_row(self, row: Dict[str, str]) -> Optional[Dict]:
        """
        Parse a single CSV row into a donation dictionary

        Args:
            row: CSV row as dictionary

        Returns:
            Donation dictionary or None if invalid
        """
        try:
            # Parse donation value
            value_str = row.get('Value', '').replace('£', '').replace(',', '').strip()
            value = Decimal(value_str) if value_str else None

            # Parse dates
            accepted_date = self._parse_date(row.get('AcceptedDate', ''))
            reported_date = self._parse_date(row.get('ReportedDate', ''))

            # Parse boolean fields
            is_sponsorship = row.get('IsSponsorship', '').lower() in ['true', 'yes', '1']
            is_irish_source = self._parse_bool(row.get('IsIrishSource', ''))
            is_bequest = row.get('IsBequest', '').lower() in ['true', 'yes', '1']
            is_aggregation = row.get('IsAggregation', '').lower() in ['true', 'yes', '1']

            donation = {
                'ec_ref': row.get('ECRef', ''),
                'donor_name': row.get('DonorName', '').strip(),
                'recipient_name': row.get('RegulatedEntityName', '').strip(),
                'value': value,
                'accepted_date': accepted_date,
                'reported_date': reported_date,
                'donation_type': row.get('DonationType', ''),
                'nature_of_donation': row.get('NatureOfDonation', ''),
                'donor_status': row.get('DonorStatus', ''),
                'company_registration_number': row.get('CompanyRegistrationNumber', ''),
                'postcode': row.get('Postcode', ''),
                'regulated_entity_name': row.get('RegulatedEntityName', ''),
                'regulated_entity_type': row.get('RegulatedDoneeType', ''),
                'campaigning_name': row.get('CampaigningName', ''),
                'register_name': row.get('RegisterName', ''),
                'is_sponsorship': is_sponsorship,
                'is_irish_source': is_irish_source,
                'is_bequest': is_bequest,
                'is_aggregation': is_aggregation,
                'accounting_units_as_central_party': row.get('AccountingUnitsAsCentralParty', ''),
                'reporting_period_name': row.get('ReportingPeriodName', ''),
                'donation_action': row.get('DonationAction', ''),
                'purpose_of_visit': row.get('PurposeOfVisit', ''),
            }

            # Validate required fields
            if not donation['ec_ref'] or not donation['donor_name']:
                logger.warning(f"Skipping row with missing required fields: {row}")
                return None

            return donation

        except Exception as e:
            logger.error(f"Error parsing row: {e}, row data: {row}")
            return None

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string into datetime object

        Args:
            date_str: Date string in various formats

        Returns:
            datetime object or None
        """
        if not date_str or date_str.strip() == '':
            return None

        date_formats = [
            '%d/%m/%Y',
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%Y/%m/%d',
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def _parse_bool(self, value: str) -> Optional[bool]:
        """Parse boolean value from string"""
        if not value or value.strip() == '':
            return None
        value_lower = value.lower().strip()
        if value_lower in ['true', 'yes', '1']:
            return True
        if value_lower in ['false', 'no', '0']:
            return False
        return None


def main():
    """
    Test the Electoral Commission parser
    """
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python -m src.ec_parser <csv_file>")
        sys.exit(1)

    parser = ECParser(sys.argv[1])
    donations = parser.parse_donations()

    print(f"\nParsed {len(donations)} donations")
    if donations:
        print("\nFirst donation:")
        for key, value in list(donations[0].items())[:10]:
            print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
