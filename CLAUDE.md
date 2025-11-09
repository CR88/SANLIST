# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**UK Sanctions List + Electoral Commission Donations Bot** - Automated system for downloading, parsing, and maintaining searchable databases of:

1. **UK Sanctions List** - Sanctioned individuals and organizations (~5,660 entities)
   - Source: https://www.gov.uk/government/publications/the-uk-sanctions-list
   - Format: XML
   - Import time: ~30-40 minutes (first import), ~5 minutes (updates)

2. **Electoral Commission Donations** - UK political donations (~89,000 donations, £1.59 billion)
   - Source: https://search.electoralcommission.org.uk (API)
   - Format: CSV
   - Import time: ~78 seconds

The system provides a unified FastAPI REST API for searching and cross-referencing between the two databases.

## Core Architecture

### Data Flow
1. **Download** ([src/downloader.py](src/downloader.py)) → Scrapes https://www.gov.uk/government/publications/the-uk-sanctions-list to find and download the latest XML file
2. **Parse** ([src/parser.py](src/parser.py)) → Extracts entities, aliases, addresses, and sanctions from the XML
3. **Database** ([src/database.py](src/database.py)) → Upserts entities and removes delisted ones from PostgreSQL
4. **API** ([src/api.py](src/api.py)) → Exposes FastAPI endpoints for searching and retrieving entities
5. **Scheduler** ([src/scheduler.py](src/scheduler.py)) → Orchestrates the entire workflow on a daily schedule

### Database Schema
The database uses SQLAlchemy models ([src/models.py](src/models.py)) with PostgreSQL full-text search:

- **entities**: Main table with `search_vector` (tsvector) for full-text search on names/titles
  - Relationships cascade delete to aliases, addresses, and sanction_regimes
- **aliases**: Alternative names linked to entities (also has `search_vector`)
- **addresses**: Structured address data
- **sanction_regimes**: Applied sanctions with regime name, type, and date
- **update_logs**: Tracks update history with counts of added/updated/deleted records

Full-text search uses PostgreSQL triggers to automatically update `search_vector` columns with weighted tsvectors (name=A, title=B, other fields=C/D).

### Key Update Logic
The `bulk_upsert()` method in [src/database.py](src/database.py) implements automatic removal of delisted entities:
1. Compares `unique_id` values between incoming XML data and existing database records
2. Updates or adds entities present in the XML
3. **Automatically deletes** entities that exist in the database but are no longer in the XML source

This ensures the database stays synchronized with the official UK sanctions list.

## Development Commands

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database (creates tables and triggers)
python manage.py init

# Run first update to populate data
python manage.py update
```

### Daily Development

```bash
# Start API server (with auto-reload for development)
python manage.py api --reload

# API available at:
# - http://localhost:8000/docs (Swagger UI)
# - http://localhost:8000/static/index.html (Web interface)

# UK Sanctions Commands
python manage.py update              # Run one-time sanctions update
python manage.py stats               # Sanctions database statistics
python manage.py search "Putin" --limit 10  # Search sanctions

# Electoral Commission Commands
python manage.py ec-init             # Initialize EC database (one-time)
python manage.py ec-update           # Download and import EC donations (~78 seconds)
python manage.py ec-stats            # EC database statistics
```

### Testing Individual Components

```bash
# Test downloader
python -m src.downloader

# Test parser (after downloading XML)
python -m src.parser data/uk_sanctions_list_*.xml

# Test database operations
python -m src.database
```

### Docker Deployment

```bash
# Start all services (PostgreSQL + scheduler)
docker-compose up -d

# Initialize database
docker-compose exec scheduler python -m src.scheduler --init-db

# Run one-time update
docker-compose exec scheduler python -m src.scheduler --once

# Check logs
docker-compose logs -f scheduler
```

### Railway Deployment

Railway uses [start.py](start.py) which:
1. Initializes database tables on startup
2. Starts scheduler in background thread (daemon)
3. Starts API server in main thread

The single service handles both API and scheduled updates.

**Update Schedule:**
- Sanctions update runs at configured time (default: 02:00 UTC)
- Electoral Commission update runs 6 hours later (default: 08:00 UTC)
- Spaced apart to prevent memory overlap on Railway's limited resources

Configuration is via environment variables (see [src/config.py](src/config.py)).

## Configuration

Environment variables (via `.env` or set directly):

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/sanctions
UPDATE_SCHEDULE_HOUR=2          # Hour for daily update (0-23)
UPDATE_SCHEDULE_MINUTE=0         # Minute for daily update (0-59)
TIMEZONE=UTC                     # Timezone for scheduling
LOG_LEVEL=INFO                   # DEBUG, INFO, WARNING, ERROR
API_HOST=0.0.0.0                 # API server host
API_PORT=8000                    # API server port
DATA_DIR=data                    # XML download directory
LOG_DIR=logs                     # Log file directory
```

## API Endpoints

### UK Sanctions List
- `GET /api/search?q={query}&limit={limit}` - Full-text search (default limit: 10000)
- `GET /api/entity/{unique_id}` - Get entity by ID (e.g., AFG0001)
- `GET /api/entities?name={name}&exact={bool}&limit={limit}` - Search by name (partial or exact)
- `GET /api/stats` - Sanctions database statistics

### Electoral Commission
- `GET /api/ec/stats` - Donations database statistics

### Cross-Reference
- `GET /api/ec/cross-check?name={name}&limit={limit}` - Check if a name appears in both sanctions and donations databases

### General
- `GET /health` - Health check

All search endpoints return full entity/donation data with nested relationships.

## Electoral Commission Integration

### Architecture
- **Downloader** ([src/ec_downloader.py](src/ec_downloader.py)) - Downloads CSV from Electoral Commission API
- **Parser** ([src/ec_parser.py](src/ec_parser.py)) - Parses CSV into donation dictionaries
- **Database** ([src/ec_database.py](src/ec_database.py)) - Upserts donations to PostgreSQL
- **Scheduler** ([src/ec_scheduler.py](src/ec_scheduler.py)) - Orchestrates download → parse → import workflow

### Database Tables
- **ec_donations** - Political donation records with full-text search on donor/recipient names
- **ec_update_logs** - Import history and statistics

### Key Features
- Automated CSV download from Electoral Commission API (`https://search.electoralcommission.org.uk/api/csv/donations`)
- Bulk imports: 89,000+ donations in ~78 seconds
- Full-text search on donor and recipient names
- Cross-reference API to check donors against sanctions list

### Cross-Referencing
The `/api/ec/cross-check` endpoint allows checking if a name appears in both:
- UK Sanctions List (sanctioned individuals/entities)
- Electoral Commission Donations (political donors)

Use case: Identify if a political donor is sanctioned, or if a sanctioned entity has made donations.

## Code Style Notes

- Uses SQLAlchemy ORM with `joinedload()` for eager loading to avoid N+1 queries
- Database sessions use context managers and are properly closed
- Full-text search converts queries to PostgreSQL `to_tsquery()` format
- Upsert operations delete old relationships before recreating to ensure clean updates
- Batch commits (every 1000 records for EC, 500 for sanctions) for optimal performance
- Logging uses Python's standard `logging` module with file and console handlers
- EC imports are 50x faster than sanctions (78 sec vs 40 min) due to simpler data structure
