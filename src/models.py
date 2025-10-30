"""
Database models for UK Sanctions List and Electoral Commission Donations
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, Date, Index, Numeric, Boolean
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import TSVECTOR

Base = declarative_base()


class Entity(Base):
    """
    Main entity table - represents sanctioned individuals or organizations
    """
    __tablename__ = 'entities'

    id = Column(Integer, primary_key=True)
    unique_id = Column(String(255), unique=True, nullable=False, index=True)  # From XML
    entity_type = Column(String(50), nullable=False)  # 'Individual' or 'Entity'
    name = Column(String(500), nullable=False)

    # Optional fields
    title = Column(String(100))
    date_of_birth = Column(Date)
    place_of_birth = Column(String(255))
    nationality = Column(String(100))
    passport_number = Column(String(100))
    national_id = Column(String(100))

    # Timestamps
    date_listed = Column(Date)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Full-text search vector
    search_vector = Column(TSVECTOR)

    # Relationships
    aliases = relationship("Alias", back_populates="entity", cascade="all, delete-orphan")
    addresses = relationship("Address", back_populates="entity", cascade="all, delete-orphan")
    sanctions = relationship("SanctionRegime", back_populates="entity", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_entity_search', 'search_vector', postgresql_using='gin'),
        Index('idx_entity_name', 'name'),
        Index('idx_entity_type', 'entity_type'),
    )

    def __repr__(self):
        return f"<Entity(id={self.id}, name='{self.name}', type='{self.entity_type}')>"


class Alias(Base):
    """
    Aliases/alternative names for entities
    """
    __tablename__ = 'aliases'

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    alias_type = Column(String(50))  # 'AKA', 'FKA', etc.
    alias_name = Column(String(500), nullable=False)

    # Full-text search vector
    search_vector = Column(TSVECTOR)

    entity = relationship("Entity", back_populates="aliases")

    __table_args__ = (
        Index('idx_alias_search', 'search_vector', postgresql_using='gin'),
        Index('idx_alias_name', 'alias_name'),
    )

    def __repr__(self):
        return f"<Alias(id={self.id}, name='{self.alias_name}')>"


class Address(Base):
    """
    Addresses associated with entities
    """
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    address_line1 = Column(String(255))
    address_line2 = Column(String(255))
    address_line3 = Column(String(255))
    city = Column(String(100))
    country = Column(String(100))
    postal_code = Column(String(20))
    full_address = Column(Text)  # Complete address as single string

    entity = relationship("Entity", back_populates="addresses")

    __table_args__ = (
        Index('idx_address_country', 'country'),
    )

    def __repr__(self):
        return f"<Address(id={self.id}, country='{self.country}')>"


class SanctionRegime(Base):
    """
    Sanctions regimes applied to entities
    """
    __tablename__ = 'sanction_regimes'

    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    regime_name = Column(String(255), nullable=False)
    regime_type = Column(String(500))  # Increased from 100 to accommodate longer regime types
    date_imposed = Column(Date)

    entity = relationship("Entity", back_populates="sanctions")

    __table_args__ = (
        Index('idx_regime_name', 'regime_name'),
    )

    def __repr__(self):
        return f"<SanctionRegime(id={self.id}, regime='{self.regime_name}')>"


class UpdateLog(Base):
    """
    Log of data updates
    """
    __tablename__ = 'update_logs'

    id = Column(Integer, primary_key=True)
    update_date = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50))  # 'success', 'failed', 'partial'
    records_updated = Column(Integer)
    records_added = Column(Integer)
    records_deleted = Column(Integer)
    error_message = Column(Text)

    def __repr__(self):
        return f"<UpdateLog(id={self.id}, status='{self.status}', date='{self.update_date}')>"


class Donation(Base):
    """
    Electoral Commission political donation records
    """
    __tablename__ = 'ec_donations'

    id = Column(Integer, primary_key=True)

    # Core donation info
    ec_ref = Column(String(100), unique=True, nullable=False, index=True)
    donor_name = Column(String(500), nullable=False, index=True)
    recipient_name = Column(String(500), nullable=False, index=True)

    # Donation details
    value = Column(Numeric(15, 2))
    accepted_date = Column(Date, index=True)
    reported_date = Column(Date)
    donation_type = Column(String(100))
    nature_of_donation = Column(String(500))

    # Donor information
    donor_status = Column(String(100))
    company_registration_number = Column(String(50))
    postcode = Column(String(20))

    # Recipient information
    regulated_entity_name = Column(String(500))
    regulated_entity_type = Column(String(100))
    campaigning_name = Column(String(500))
    register_name = Column(String(50))

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
    status = Column(String(50))
    records_updated = Column(Integer)
    records_added = Column(Integer)
    records_deleted = Column(Integer)
    file_path = Column(String(1000))
    error_message = Column(Text)

    def __repr__(self):
        return f"<ECUpdateLog(id={self.id}, status='{self.status}', date='{self.update_date}')>"
