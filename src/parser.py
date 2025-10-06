"""
Parser module for UK Sanctions List XML
Extracts entity information, aliases, addresses, and sanctions regimes
"""
import logging
from typing import List, Dict, Optional
from datetime import datetime
from lxml import etree

logger = logging.getLogger(__name__)


class SanctionsParser:
    """
    Parses UK Sanctions List XML files
    """

    def __init__(self, xml_filepath: str):
        self.xml_filepath = xml_filepath
        self.tree = None
        self.root = None

    def load_xml(self) -> bool:
        """
        Load and parse XML file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info(f"Loading XML file: {self.xml_filepath}")
            self.tree = etree.parse(self.xml_filepath)
            self.root = self.tree.getroot()
            logger.info("XML file loaded successfully")
            return True
        except Exception as e:
            logger.error(f"Error loading XML file: {e}")
            return False

    def _get_text(self, element, xpath: str, default: str = "") -> str:
        """
        Safely extract text from XML element using XPath

        Args:
            element: XML element
            xpath: XPath expression
            default: Default value if not found

        Returns:
            str: Extracted text or default
        """
        try:
            result = element.xpath(xpath)
            if result and len(result) > 0:
                if isinstance(result[0], str):
                    return result[0].strip()
                elif hasattr(result[0], 'text') and result[0].text:
                    return result[0].text.strip()
            return default
        except Exception as e:
            logger.debug(f"Error extracting text with xpath '{xpath}': {e}")
            return default

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime object

        Args:
            date_str: Date string in various formats

        Returns:
            datetime: Parsed date or None
        """
        if not date_str:
            return None

        date_formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d %B %Y",
            "%B %d, %Y"
        ]

        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse date: {date_str}")
        return None

    def parse_entities(self) -> List[Dict]:
        """
        Parse all entities (individuals and organizations) from XML

        Returns:
            List[Dict]: List of parsed entity dictionaries
        """
        if not self.root:
            logger.error("XML not loaded. Call load_xml() first.")
            return []

        entities = []

        # Try different possible root structures
        # UK sanctions list uses Designation as the main entity element
        entity_paths = [
            ".//Designation",
            ".//Individual",
            ".//Entity",
            ".//target",
            ".//sanctionedEntity"
        ]

        for path in entity_paths:
            entity_elements = self.root.xpath(path)
            if entity_elements:
                logger.info(f"Found {len(entity_elements)} entities using path: {path}")
                for elem in entity_elements:
                    entity = self._parse_entity(elem, path)
                    if entity:
                        entities.append(entity)
                break

        logger.info(f"Parsed {len(entities)} total entities")
        return entities

    def _parse_entity(self, elem, entity_type_path: str) -> Optional[Dict]:
        """
        Parse a single entity element

        Args:
            elem: XML element
            entity_type_path: XPath that identified this entity

        Returns:
            Dict: Parsed entity data
        """
        try:
            # Extract unique ID
            unique_id = self._get_text(elem, './/UniqueID/text()') or elem.get('id') or elem.get('ID')

            # Determine entity type from IndividualEntityShip field
            entity_type_str = self._get_text(elem, './/IndividualEntityShip/text()')
            entity_type = entity_type_str if entity_type_str in ['Individual', 'Entity'] else "Entity"

            # Extract primary name from Names/Name where NameType is "Primary Name"
            name = None
            names_elements = elem.xpath('.//Names/Name')
            for name_elem in names_elements:
                name_type = self._get_text(name_elem, './/NameType/text()')
                if name_type == 'Primary Name':
                    name = self._get_text(name_elem, './/Name6/text()')
                    break

            # Fallback to first name if no primary name found
            if not name and names_elements:
                name = self._get_text(names_elements[0], './/Name6/text()')

            if not name:
                logger.warning(f"Entity without name found, ID: {unique_id}")
                return None

            entity = {
                'unique_id': unique_id,
                'entity_type': entity_type,
                'name': name,
                'title': self._get_text(elem, './/Title/text()'),
                'date_of_birth': None,
                'place_of_birth': self._get_text(elem, './/PlaceOfBirth/text()') or self._get_text(elem, './/TownOfBirth/text()'),
                'nationality': self._get_text(elem, './/Nationality/text()') or self._get_text(elem, './/CountryOfBirth/text()'),
                'passport_number': self._get_text(elem, './/PassportNumber/text()'),
                'national_id': self._get_text(elem, './/NationalIDNumber/text()'),
                'date_listed': None,
                'aliases': self._parse_aliases(elem),
                'addresses': self._parse_addresses(elem),
                'sanctions': self._parse_sanctions(elem)
            }

            # Parse dates
            dob_str = self._get_text(elem, './/DOB/text()') or self._get_text(elem, './/DateOfBirth/text()')
            if dob_str:
                entity['date_of_birth'] = self._parse_date(dob_str)

            date_listed_str = self._get_text(elem, './/DateDesignated/text()') or self._get_text(elem, './/DateListed/text()')
            if date_listed_str:
                entity['date_listed'] = self._parse_date(date_listed_str)

            return entity

        except Exception as e:
            logger.error(f"Error parsing entity: {e}")
            return None

    def _parse_aliases(self, elem) -> List[Dict]:
        """
        Parse aliases/alternative names for an entity

        Args:
            elem: Entity XML element

        Returns:
            List[Dict]: List of alias dictionaries
        """
        aliases = []

        # UK Sanctions List: aliases are in Names/Name where NameType is "Alias"
        names_elements = elem.xpath('.//Names/Name')
        for name_elem in names_elements:
            name_type = self._get_text(name_elem, './/NameType/text()')
            if name_type == 'Alias' or name_type == 'AKA':
                alias_name = self._get_text(name_elem, './/Name6/text()')
                if alias_name:
                    aliases.append({
                        'alias_type': name_type,
                        'alias_name': alias_name
                    })

        return aliases

    def _parse_addresses(self, elem) -> List[Dict]:
        """
        Parse addresses for an entity

        Args:
            elem: Entity XML element

        Returns:
            List[Dict]: List of address dictionaries
        """
        addresses = []

        address_elements = elem.xpath('.//Addresses/Address')

        for addr_elem in address_elements:
            # UK Sanctions List uses AddressLine1-6, AddressCountry, AddressPostCode
            lines = []
            for i in range(1, 7):
                line = self._get_text(addr_elem, f'.//AddressLine{i}/text()')
                if line:
                    lines.append(line)

            address = {
                'address_line1': self._get_text(addr_elem, './/AddressLine1/text()'),
                'address_line2': self._get_text(addr_elem, './/AddressLine2/text()'),
                'address_line3': self._get_text(addr_elem, './/AddressLine3/text()'),
                'city': None,  # Not explicitly in UK schema, might be in AddressLine5
                'country': self._get_text(addr_elem, './/AddressCountry/text()') or self._get_text(addr_elem, './/Country/text()'),
                'postal_code': self._get_text(addr_elem, './/AddressPostCode/text()') or self._get_text(addr_elem, './/PostCode/text()'),
                'full_address': ', '.join(lines) if lines else None
            }

            if address['full_address'] or address['address_line1'] or address['country']:
                addresses.append(address)

        return addresses

    def _parse_sanctions(self, elem) -> List[Dict]:
        """
        Parse sanctions regimes for an entity

        Args:
            elem: Entity XML element

        Returns:
            List[Dict]: List of sanction regime dictionaries
        """
        sanctions = []

        # UK Sanctions List: RegimeName is a direct child of Designation
        regime_name = self._get_text(elem, './/RegimeName/text()')

        if regime_name:
            # Also get SanctionsImposed which describes the type of sanctions
            sanctions_type = self._get_text(elem, './/SanctionsImposed/text()')
            date_designated = self._get_text(elem, './/DateDesignated/text()')

            sanctions.append({
                'regime_name': regime_name,
                'regime_type': sanctions_type,
                'date_imposed': self._parse_date(date_designated) if date_designated else None
            })

        return sanctions


def main():
    """
    Main function for testing the parser
    """
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 2:
        print("Usage: python parser.py <xml_file>")
        sys.exit(1)

    xml_file = sys.argv[1]
    parser = SanctionsParser(xml_file)

    if parser.load_xml():
        entities = parser.parse_entities()
        print(f"\n✓ Parsed {len(entities)} entities")

        if entities:
            print("\nFirst entity sample:")
            first = entities[0]
            print(f"  Name: {first['name']}")
            print(f"  Type: {first['entity_type']}")
            print(f"  Aliases: {len(first['aliases'])}")
            print(f"  Addresses: {len(first['addresses'])}")
            print(f"  Sanctions: {len(first['sanctions'])}")
    else:
        print("✗ Failed to load XML")


if __name__ == "__main__":
    main()
