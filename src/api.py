"""
FastAPI REST API for UK Sanctions List
"""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from .config import Config
from .database import SanctionsDatabase

# Initialize FastAPI app
app = FastAPI(
    title="UK Sanctions List API",
    description="REST API for searching UK sanctions list data",
    version="1.0.0"
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

# Initialize database
db = SanctionsDatabase(Config.DATABASE_URL)


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
        results = db.search(q, limit=limit)

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
    entity = db.get_entity_by_id(unique_id)

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
        results = db.search_by_name(name, exact=exact)[:limit]

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
        stats = db.get_stats()
        return StatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=Config.API_HOST, port=Config.API_PORT)
