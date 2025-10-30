"""
Database models for Electoral Commission Political Donations
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Numeric, Text, Boolean, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import TSVECTOR

from .models import Base


class Donation(Base):
    """
    Electoral Commission political donation records
    """
    __tablename__ = 'ec_donations'

    id = Column(Integer, primary_key=True)

    # Core donation info
    ec_ref = Column(String(100), unique=True, nullable=False, index=True)  # Electoral Commission reference
    donor_name = Column(String(500), nullable=False, index=True)
    recipient_name = Column(String(500), nullable=False, index=True)  # Regulated entity receiving donation

    # Donation details
    value = Column(Numeric(15, 2))  # Donation amount
    accepted_date = Column(Date, index=True)
    reported_date = Column(Date)
    donation_type = Column(String(100))  # e.g., Cash, Non-cash, Visit
    nature_of_donation = Column(String(500))

    # Donor information
    donor_status = Column(String(100))  # Individual, Company, Trade Union, etc.
    company_registration_number = Column(String(50))
    postcode = Column(String(20))

    # Recipient information
    regulated_entity_name = Column(String(500))
    regulated_entity_type = Column(String(100))  # PP (Political Party), etc.
    campaigning_name = Column(String(500))
    register_name = Column(String(50))  # GB, NI, or None

    # Additional fields
    is_sponsorship = Column(Boolean, default=False)
    is_irish_source = Column(Boolean)
    is_bequest = Column(Boolean, default=False)
    is_aggregation = Column(Boolean, default=False)
    accounting_units_as_central_party = Column(String(500))
    reporting_period_name = Column(String(100))
    donation_action = Column(String(100))
    purpose_of_visit = Column(Text)

    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Full-text search vector
    search_vector = Column(TSVECTOR)

    __table_args__ = (
        Index('idx_donation_search', 'search_vector', postgresql_using='gin'),
        Index('idx_donation_donor_name', 'donor_name'),
        Index('idx_donation_recipient_name', 'recipient_name'),
        Index('idx_donation_value', 'value'),
        Index('idx_donation_accepted_date', 'accepted_date'),
    )

    def __repr__(self):
        return f"<Donation(id={self.id}, donor='{self.donor_name}', value={self.value})>"


class ECUpdateLog(Base):
    """
    Log of Electoral Commission data updates
    """
    __tablename__ = 'ec_update_logs'

    id = Column(Integer, primary_key=True)
    update_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50))  # 'success', 'failed', 'partial'
    records_updated = Column(Integer)
    records_added = Column(Integer)
    records_deleted = Column(Integer)
    file_url = Column(String(1000))
    error_message = Column(Text)

    def __repr__(self):
        return f"<ECUpdateLog(id={self.id}, status='{self.status}', date='{self.update_date}')>"
