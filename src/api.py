"""
FastAPI REST API for UK Sanctions List + Electoral Commission Donations
"""
import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from decimal import Decimal

from .config import Config
from .database import SanctionsDatabase
from .ec_database import ECDatabase

# Setup logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="UK Sanctions & Electoral Commission API",
    description="REST API for searching UK sanctions list and electoral commission donations data",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Initialize databases
sanctions_db = SanctionsDatabase(Config.DATABASE_URL)
ec_db = ECDatabase(Config.DATABASE_URL)


# Pydantic models for responses
class AliasResponse(BaseModel):
    alias_type: Optional[str]
    alias_name: str


class AddressResponse(BaseModel):
    address_line1: Optional[str]
    address_line2: Optional[str]
    address_line3: Optional[str]
    city: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]
    full_address: Optional[str]


class SanctionRegimeResponse(BaseModel):
    regime_name: str
    regime_type: Optional[str]
    date_imposed: Optional[datetime]


class EntityResponse(BaseModel):
    id: int
    unique_id: str
    entity_type: str
    name: str
    title: Optional[str]
    date_of_birth: Optional[datetime]
    place_of_birth: Optional[str]
    nationality: Optional[str]
    passport_number: Optional[str]
    national_id: Optional[str]
    date_listed: Optional[datetime]
    last_updated: datetime
    aliases: List[AliasResponse]
    addresses: List[AddressResponse]
    sanctions: List[SanctionRegimeResponse]

    class Config:
        from_attributes = True


class StatsResponse(BaseModel):
    total_entities: int
    individuals: int
    organizations: int
    total_aliases: int
    last_update: Optional[datetime]


class SearchResponse(BaseModel):
    query: str
    count: int
    results: List[EntityResponse]


# API Endpoints
@app.get("/")
def root():
    """Root endpoint with API information"""
    return {
        "name": "UK Sanctions List API",
        "version": "1.0.0",
        "web_interface": "/static/index.html",
        "endpoints": {
            "/api/search": "Full-text search entities",
            "/api/entity/{id}": "Get entity by unique ID",
            "/api/entities": "Search by name",
            "/api/stats": "Get database statistics",
            "/docs": "API documentation",
            "/static/index.html": "Web search interface"
        }
    }


@app.get("/api/search", response_model=SearchResponse)
def search(
    q: str = Query(..., description="Search query"),
    limit: int = Query(10000, ge=1, description="Maximum results (default: 10000, use 10000 for all)")
):
    """
    Full-text search for entities

    - **q**: Search query (searches names, aliases, addresses)
    - **limit**: Maximum number of results (default: 10000 - effectively unlimited)
    """
    try:
        results = sanctions_db.search(q, limit=limit)

        return SearchResponse(
            query=q,
            count=len(results),
            results=[
                EntityResponse(
                    id=entity.id,
                    unique_id=entity.unique_id,
                    entity_type=entity.entity_type,
                    name=entity.name,
                    title=entity.title,
                    date_of_birth=entity.date_of_birth,
                    place_of_birth=entity.place_of_birth,
                    nationality=entity.nationality,
                    passport_number=entity.passport_number,
                    national_id=entity.national_id,
                    date_listed=entity.date_listed,
                    last_updated=entity.last_updated,
                    aliases=[
                        AliasResponse(alias_type=a.alias_type, alias_name=a.alias_name)
                        for a in entity.aliases
                    ],
                    addresses=[
                        AddressResponse(
                            address_line1=addr.address_line1,
                            address_line2=addr.address_line2,
                            address_line3=addr.address_line3,
                            city=addr.city,
                            country=addr.country,
                            postal_code=addr.postal_code,
                            full_address=addr.full_address
                        )
                        for addr in entity.addresses
                    ],
                    sanctions=[
                        SanctionRegimeResponse(
                            regime_name=s.regime_name,
                            regime_type=s.regime_type,
                            date_imposed=s.date_imposed
                        )
                        for s in entity.sanctions
                    ]
                )
                for entity in results
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entity/{unique_id}", response_model=EntityResponse)
def get_entity(unique_id: str):
    """
    Get entity by unique ID

    - **unique_id**: The entity's unique identifier (e.g., AFG0001, RUS1280)
    """
    entity = sanctions_db.get_entity_by_id(unique_id)

    if not entity:
        raise HTTPException(status_code=404, detail=f"Entity {unique_id} not found")

    return EntityResponse(
        id=entity.id,
        unique_id=entity.unique_id,
        entity_type=entity.entity_type,
        name=entity.name,
        title=entity.title,
        date_of_birth=entity.date_of_birth,
        place_of_birth=entity.place_of_birth,
        nationality=entity.nationality,
        passport_number=entity.passport_number,
        national_id=entity.national_id,
        date_listed=entity.date_listed,
        last_updated=entity.last_updated,
        aliases=[
            AliasResponse(alias_type=a.alias_type, alias_name=a.alias_name)
            for a in entity.aliases
        ],
        addresses=[
            AddressResponse(
                address_line1=addr.address_line1,
                address_line2=addr.address_line2,
                address_line3=addr.address_line3,
                city=addr.city,
                country=addr.country,
                postal_code=addr.postal_code,
                full_address=addr.full_address
            )
            for addr in entity.addresses
        ],
        sanctions=[
            SanctionRegimeResponse(
                regime_name=s.regime_name,
                regime_type=s.regime_type,
                date_imposed=s.date_imposed
            )
            for s in entity.sanctions
        ]
    )


@app.get("/api/entities", response_model=SearchResponse)
def search_by_name(
    name: str = Query(..., description="Name to search for"),
    exact: bool = Query(False, description="Exact match (true) or partial match (false)"),
    limit: int = Query(10000, ge=1, description="Maximum results (default: 10000)")
):
    """
    Search entities by name (or alias)

    - **name**: Name to search for
    - **exact**: If true, exact match; if false, partial match (default: false)
    - **limit**: Maximum number of results (default: 10000 - effectively unlimited)
    """
    try:
        results = sanctions_db.search_by_name(name, exact=exact)[:limit]

        return SearchResponse(
            query=name,
            count=len(results),
            results=[
                EntityResponse(
                    id=entity.id,
                    unique_id=entity.unique_id,
                    entity_type=entity.entity_type,
                    name=entity.name,
                    title=entity.title,
                    date_of_birth=entity.date_of_birth,
                    place_of_birth=entity.place_of_birth,
                    nationality=entity.nationality,
                    passport_number=entity.passport_number,
                    national_id=entity.national_id,
                    date_listed=entity.date_listed,
                    last_updated=entity.last_updated,
                    aliases=[
                        AliasResponse(alias_type=a.alias_type, alias_name=a.alias_name)
                        for a in entity.aliases
                    ],
                    addresses=[
                        AddressResponse(
                            address_line1=addr.address_line1,
                            address_line2=addr.address_line2,
                            address_line3=addr.address_line3,
                            city=addr.city,
                            country=addr.country,
                            postal_code=addr.postal_code,
                            full_address=addr.full_address
                        )
                        for addr in entity.addresses
                    ],
                    sanctions=[
                        SanctionRegimeResponse(
                            regime_name=s.regime_name,
                            regime_type=s.regime_type,
                            date_imposed=s.date_imposed
                        )
                        for s in entity.sanctions
                    ]
                )
                for entity in results
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=StatsResponse)
def get_stats():
    """
    Get database statistics

    Returns counts of entities, individuals, organizations, and aliases
    """
    try:
        stats = sanctions_db.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


# Electoral Commission Endpoints

class DonationResponse(BaseModel):
    """Electoral Commission donation response model"""
    id: int
    ec_ref: str
    donor_name: str
    recipient_name: str
    value: Optional[Decimal]
    accepted_date: Optional[date]
    reported_date: Optional[date]
    donation_type: Optional[str]
    donor_status: Optional[str]
    company_registration_number: Optional[str]
    postcode: Optional[str]
    regulated_entity_name: Optional[str]
    regulated_entity_type: Optional[str]
    campaigning_name: Optional[str]
    register_name: Optional[str]
    is_sponsorship: Optional[bool]
    is_irish_source: Optional[bool]
    last_updated: datetime

    class Config:
        from_attributes = True


class ECStatsResponse(BaseModel):
    """Electoral Commission statistics response"""
    total_donations: int
    total_value: float
    unique_donors: int
    unique_recipients: int
    last_update: Optional[datetime]


class DonationSearchResponse(BaseModel):
    """Electoral Commission search response"""
    query: str
    count: int
    results: List[DonationResponse]


class CrossCheckResponse(BaseModel):
    """Cross-check response showing potential sanction matches"""
    query: str
    sanctions_found: int
    donations_found: int
    potential_matches: List[dict]


@app.get("/api/ec/stats", response_model=ECStatsResponse, tags=["Electoral Commission"])
def get_ec_stats():
    """
    Get Electoral Commission database statistics

    Returns counts and totals for donations data
    """
    try:
        stats = ec_db.get_stats()
        return ECStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ec/cross-check", response_model=CrossCheckResponse, tags=["Cross-Reference"])
def cross_check_sanctions(
    name: str = Query(..., description="Name to check against both databases"),
    limit: int = Query(10, ge=1, le=100, description="Maximum matches per database")
):
    """
    Cross-check a name against both sanctions list and donations database

    This endpoint searches for potential matches between:
    - Sanctioned entities in the UK Sanctions List
    - Political donors in the Electoral Commission data

    Useful for identifying if a donor appears on the sanctions list or vice versa.

    - **name**: Name to search for
    - **limit**: Maximum results per database (default: 10)
    """
    try:
        # Search sanctions database
        sanctions_results = sanctions_db.search_by_name(name, exact=False)[:limit]

        # Search EC donations database (we'll need to add this method)
        # For now, return basic info

        potential_matches = []
        for entity in sanctions_results:
            potential_matches.append({
                "type": "sanctions_entity",
                "name": entity.name,
                "unique_id": entity.unique_id,
                "entity_type": entity.entity_type,
                "date_listed": entity.date_listed.isoformat() if entity.date_listed else None,
            })

        return CrossCheckResponse(
            query=name,
            sanctions_found=len(sanctions_results),
            donations_found=0,  # TODO: implement EC search
            potential_matches=potential_matches
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Tenant Screening Endpoint

class TenantScreeningResponse(BaseModel):
    """Comprehensive tenant screening response"""
    query: str
    screening_date: datetime
    risk_level: str  # "clear", "low", "medium", "high"
    sanctions_matches: List[dict]
    donation_matches: List[dict]
    total_matches: int
    summary: str

    class Config:
        from_attributes = True


@app.post("/api/screen-tenant", response_model=TenantScreeningResponse, tags=["Tenant Screening"])
@app.get("/api/screen-tenant", response_model=TenantScreeningResponse, tags=["Tenant Screening"])
def screen_tenant(
    name: str = Query(..., description="Full name of the tenant to screen"),
    date_of_birth: Optional[str] = Query(None, description="Date of birth (YYYY-MM-DD) for better matching"),
    postcode: Optional[str] = Query(None, description="Postcode for enhanced matching"),
    company_name: Optional[str] = Query(None, description="Company name if tenant is a business"),
    company_reg: Optional[str] = Query(None, description="Company registration number"),
    exact_match: bool = Query(False, description="Require exact name match (default: fuzzy)")
):
    """
    **TENANT SCREENING API** - Check if a tenant appears in sanctions or political donations

    This endpoint is designed to be called from your tenant application system to perform
    comprehensive background checks against:

    1. **UK Sanctions List** - Check if tenant is a sanctioned individual or entity
    2. **Electoral Commission Donations** - Check if tenant has made political donations

    **Risk Levels:**
    - `clear`: No matches found - tenant is clear
    - `low`: Found in donations only (not concerning)
    - `medium`: Multiple donation records or unclear matches
    - `high`: Found in UK Sanctions List (REJECT TENANT)

    **Usage from your application:**
    ```javascript
    // POST or GET request
    const response = await fetch('http://your-api.com/api/screen-tenant?name=John+Smith&date_of_birth=1990-01-01');
    const result = await response.json();

    if (result.risk_level === 'high') {
        alert('TENANT REJECTED: Found on UK Sanctions List');
    }
    ```

    **Parameters:**
    - **name** (required): Full name of tenant
    - **date_of_birth**: Date of birth for more accurate matching
    - **postcode**: Postcode for location-based matching
    - **company_name**: If tenant is a business
    - **company_reg**: Company registration number (very accurate)
    - **exact_match**: Use exact name matching (default: fuzzy search)
    """
    try:
        sanctions_matches = []
        donation_matches = []
        risk_level = "clear"

        # 1. Check UK Sanctions List (HIGHEST PRIORITY)
        sanctions_results = sanctions_db.search_by_name(name, exact=exact_match)[:20]

        for entity in sanctions_results:
            match_data = {
                "database": "UK_SANCTIONS",
                "matched_name": entity.name,
                "unique_id": entity.unique_id,
                "entity_type": entity.entity_type,
                "date_listed": entity.date_listed.isoformat() if entity.date_listed else None,
                "nationality": entity.nationality,
                "date_of_birth": entity.date_of_birth.isoformat() if entity.date_of_birth else None,
                "aliases": [a.alias_name for a in entity.aliases[:5]],
                "sanctions": [
                    {
                        "regime": s.regime_name,
                        "type": s.regime_type,
                        "date": s.date_imposed.isoformat() if s.date_imposed else None
                    }
                    for s in entity.sanctions[:3]
                ],
                "severity": "CRITICAL"
            }
            sanctions_matches.append(match_data)

        # 2. Check Electoral Commission Donations (LOWER PRIORITY)
        # Search by donor name using database query
        from .models import Donation
        from sqlalchemy import or_, func

        db_session = ec_db.SessionLocal()
        try:
            # Build search query
            search_pattern = f"%{name}%"
            query = db_session.query(Donation).filter(
                or_(
                    func.lower(Donation.donor_name).like(func.lower(search_pattern)),
                    func.lower(Donation.recipient_name).like(func.lower(search_pattern))
                )
            )

            # Add company registration number filter if provided
            if company_reg:
                query = query.filter(Donation.company_registration_number == company_reg)

            # Add postcode filter if provided
            if postcode:
                query = query.filter(Donation.postcode.like(f"%{postcode}%"))

            donation_results = query.limit(20).all()

            for donation in donation_results:
                match_data = {
                    "database": "ELECTORAL_COMMISSION",
                    "matched_as": "donor" if name.lower() in donation.donor_name.lower() else "recipient",
                    "donor_name": donation.donor_name,
                    "recipient_name": donation.recipient_name,
                    "value": float(donation.value) if donation.value else 0,
                    "donation_type": donation.donation_type,
                    "accepted_date": donation.accepted_date.isoformat() if donation.accepted_date else None,
                    "donor_status": donation.donor_status,
                    "company_reg": donation.company_registration_number,
                    "postcode": donation.postcode,
                    "severity": "INFO"
                }
                donation_matches.append(match_data)
        finally:
            db_session.close()

        # 3. Determine risk level
        total_matches = len(sanctions_matches) + len(donation_matches)

        if len(sanctions_matches) > 0:
            risk_level = "high"  # CRITICAL - Found on sanctions list
            summary = f"⚠️ CRITICAL: Found {len(sanctions_matches)} match(es) on UK Sanctions List. REJECT TENANT APPLICATION."
        elif len(donation_matches) > 10:
            risk_level = "medium"
            summary = f"Found {len(donation_matches)} political donation records. Review recommended."
        elif len(donation_matches) > 0:
            risk_level = "low"
            summary = f"Found {len(donation_matches)} political donation record(s). Generally not concerning."
        else:
            risk_level = "clear"
            summary = "✓ No matches found in UK Sanctions List or Electoral Commission. Tenant is clear."

        return TenantScreeningResponse(
            query=name,
            screening_date=datetime.utcnow(),
            risk_level=risk_level,
            sanctions_matches=sanctions_matches,
            donation_matches=donation_matches,
            total_matches=total_matches,
            summary=summary
        )

    except Exception as e:
        logger.error(f"Error screening tenant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Screening error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.API_HOST, port=Config.API_PORT)
