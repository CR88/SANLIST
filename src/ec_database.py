"""
Electoral Commission database operations
"""
import logging
from typing import List, Dict, Tuple
from datetime import datetime
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, Donation, ECUpdateLog

logger = logging.getLogger(__name__)


class ECDatabase:
    """
    Manages database operations for Electoral Commission donations
    """

    def __init__(self, database_url: str):
        """
        Initialize database connection

        Args:
            database_url: PostgreSQL connection string
        """
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        """
        Create Electoral Commission database tables
        """
        try:
            logger.info("Creating Electoral Commission tables...")
            Base.metadata.create_all(self.engine, tables=[
                Donation.__table__,
                ECUpdateLog.__table__
            ])
            logger.info("Electoral Commission tables created successfully")

            # Create full-text search triggers
            self._create_search_triggers()

        except Exception as e:
            logger.error(f"Error creating EC tables: {e}")
            raise

    def _create_search_triggers(self):
        """
        Create PostgreSQL triggers for automatic full-text search vector updates
        """
        try:
            with self.engine.connect() as conn:
                # Trigger for donations table
                conn.execute(text("""
                    CREATE OR REPLACE FUNCTION donations_search_trigger() RETURNS trigger AS $$
                    BEGIN
                        NEW.search_vector :=
                            setweight(to_tsvector('english', coalesce(NEW.donor_name, '')), 'A') ||
                            setweight(to_tsvector('english', coalesce(NEW.recipient_name, '')), 'A') ||
                            setweight(to_tsvector('english', coalesce(NEW.regulated_entity_name, '')), 'B') ||
                            setweight(to_tsvector('english', coalesce(NEW.campaigning_name, '')), 'B') ||
                            setweight(to_tsvector('english', coalesce(NEW.company_registration_number, '')), 'C');
                        RETURN NEW;
                    END
                    $$ LANGUAGE plpgsql;
                """))

                conn.execute(text("""
                    DROP TRIGGER IF EXISTS donations_search_update ON ec_donations;
                    CREATE TRIGGER donations_search_update BEFORE INSERT OR UPDATE
                    ON ec_donations FOR EACH ROW EXECUTE FUNCTION donations_search_trigger();
                """))

                conn.commit()
                logger.info("EC search triggers created successfully")

        except Exception as e:
            logger.error(f"Error creating EC search triggers: {e}")
            raise

    def bulk_upsert(self, donations_data: List[Dict], file_path: str = None) -> Tuple[int, int, int]:
        """
        Bulk upsert donations

        Args:
            donations_data: List of donation dictionaries
            file_path: Optional file path for logging

        Returns:
            Tuple[int, int, int]: (added, updated, errors)
        """
        added = 0
        updated = 0
        errors = 0

        db = self.SessionLocal()

        try:
            logger.info(f"Starting bulk upsert of {len(donations_data)} donations...")

            # Get existing EC refs
            existing_refs = {d.ec_ref for d in db.query(Donation.ec_ref).all()}

            # Split into updates and inserts
            donations_to_insert = []
            donations_to_update = []

            for donation_data in donations_data:
                if donation_data['ec_ref'] in existing_refs:
                    donations_to_update.append(donation_data)
                else:
                    donations_to_insert.append(donation_data)

            logger.info(f"Split: {len(donations_to_insert)} new, {len(donations_to_update)} to update")

            # Process updates
            if donations_to_update:
                logger.info("Processing updates...")
                for donation_data in donations_to_update:
                    try:
                        donation = db.query(Donation).filter_by(ec_ref=donation_data['ec_ref']).first()
                        if donation:
                            for key, value in donation_data.items():
                                if key != 'ec_ref':
                                    setattr(donation, key, value)
                            donation.last_updated = datetime.utcnow()
                            updated += 1

                            if updated % 1000 == 0:
                                db.commit()
                                logger.info(f"Progress: {updated}/{len(donations_to_update)} updated")

                    except Exception as e:
                        logger.error(f"Error updating donation {donation_data.get('ec_ref')}: {e}")
                        errors += 1
                        db.rollback()

                db.commit()
                logger.info(f"Completed {updated} updates")

            # Process inserts in bulk
            if donations_to_insert:
                logger.info(f"Bulk inserting {len(donations_to_insert)} new donations...")
                batch_size = 1000

                for i in range(0, len(donations_to_insert), batch_size):
                    batch = donations_to_insert[i:i + batch_size]
                    try:
                        for donation_data in batch:
                            donation = Donation(**donation_data)
                            db.add(donation)
                            added += 1

                        db.commit()
                        logger.info(f"Progress: {added}/{len(donations_to_insert)} inserted")

                    except Exception as e:
                        logger.error(f"Error in bulk insert batch: {e}")
                        errors += len(batch)
                        db.rollback()

            logger.info(f"Upsert complete: {added} added, {updated} updated, {errors} errors")

            # Log the update
            update_log = ECUpdateLog(
                status='success' if errors == 0 else 'partial',
                records_added=added,
                records_updated=updated,
                records_deleted=0,
                file_path=file_path,
                error_message=f"{errors} errors" if errors > 0 else None
            )
            db.add(update_log)
            db.commit()

            return added, updated, errors

        except Exception as e:
            logger.error(f"Error in bulk upsert: {e}")
            db.rollback()
            raise
        finally:
            db.close()

    def get_stats(self) -> Dict:
        """
        Get database statistics

        Returns:
            Dict: Statistics about the EC database
        """
        db = self.SessionLocal()

        try:
            total_donations = db.query(Donation).count()
            total_value = db.query(func.sum(Donation.value)).scalar() or 0
            unique_donors = db.query(Donation.donor_name).distinct().count()
            unique_recipients = db.query(Donation.recipient_name).distinct().count()
            last_update = db.query(ECUpdateLog).order_by(ECUpdateLog.update_date.desc()).first()

            return {
                'total_donations': total_donations,
                'total_value': float(total_value),
                'unique_donors': unique_donors,
                'unique_recipients': unique_recipients,
                'last_update': last_update.update_date if last_update else None
            }
        finally:
            db.close()


def main():
    """
    Test EC database operations
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    db_url = os.getenv('DATABASE_URL')
    db = ECDatabase(db_url)

    # Create tables
    db.create_tables()

    # Get stats
    stats = db.get_stats()
    print(f"\nElectoral Commission Database Statistics:")
    print(f"  Total Donations: {stats['total_donations']:,}")
    print(f"  Total Value: £{stats['total_value']:,.2f}")
    print(f"  Unique Donors: {stats['unique_donors']:,}")
    print(f"  Unique Recipients: {stats['unique_recipients']:,}")
    print(f"  Last Update: {stats['last_update']}")


if __name__ == "__main__":
    main()
