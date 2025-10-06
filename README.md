# UK Sanctions List Bot

Automated system for downloading, parsing, and maintaining a searchable database of the UK Sanctions List.

## Features

- 📥 **Automated Downloads**: Daily scraping and downloading of UK sanctions list (XML format)
- 🔄 **Smart Updates**: Upsert logic to handle daily updates efficiently
- 🔍 **Full-Text Search**: PostgreSQL-powered search with ranking
- 📊 **Database Storage**: Structured PostgreSQL database with entities, aliases, addresses, and sanctions
- ⏰ **Scheduled Updates**: Configurable daily updates
- 🐳 **Docker Support**: Easy deployment with Docker Compose

## Architecture

```
sanctions/
├── src/
│   ├── downloader.py      # Scrapes gov.uk and downloads XML
│   ├── parser.py          # Parses XML and extracts data
│   ├── database.py        # PostgreSQL operations (upsert, search)
│   ├── models.py          # SQLAlchemy database models
│   ├── scheduler.py       # Daily update scheduler
│   └── config.py          # Configuration management
├── data/                  # Downloaded XML files
├── logs/                  # Application logs
├── docker-compose.yml     # Docker services
└── requirements.txt       # Python dependencies
```

## Quick Start

### Option 1: Railway (Easiest - One-Click Deploy)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/new)

1. **Click the button above or manual setup**:
   - Go to [Railway](https://railway.app)
   - Create new project from GitHub repo
   - Connect your GitHub account and select this repo

2. **Add PostgreSQL service**:
   - In your Railway project, click "+ New"
   - Select "Database" → "PostgreSQL"
   - Railway automatically sets `DATABASE_URL`

3. **Configure environment variables** (optional):
   - `UPDATE_SCHEDULE_HOUR` - Hour to run daily update (default: 2)
   - `TIMEZONE` - Timezone for scheduling (default: UTC)
   - `LOG_LEVEL` - Logging verbosity (default: INFO)

4. **Deploy**:
   - Railway automatically deploys on git push
   - Get your app URL from Railway dashboard
   - Access API docs at: `https://your-app.railway.app/docs`
   - Web interface at: `https://your-app.railway.app/static/index.html`

5. **Run initial data update**:
   ```bash
   # Using Railway CLI
   railway run python manage.py update

   # Or via Railway dashboard → Variables → Add RUN_UPDATE=true
   ```

6. **Setup scheduler (for daily updates)**:
   - Create a second service in Railway
   - Use same GitHub repo
   - Set custom start command: `python -m src.scheduler`
   - Uses the same DATABASE_URL automatically

**That's it!** Your API is live and ready to use.

### Option 2: Docker (Recommended for Self-Hosting)

1. **Clone and setup**:
   ```bash
   git clone <repository-url>
   cd sanctions
   cp .env.example .env
   ```

2. **Start services**:
   ```bash
   docker-compose up -d
   ```

3. **Initialize database**:
   ```bash
   docker-compose exec scheduler python -m src.scheduler --init-db
   ```

4. **Run first update**:
   ```bash
   docker-compose exec scheduler python -m src.scheduler --once
   ```

The scheduler will now run daily updates automatically at 2 AM UTC (configurable in `.env`).

### Option 3: Local Installation

1. **Prerequisites**:
   - Python 3.11+
   - PostgreSQL 12+

2. **Install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Setup PostgreSQL**:
   ```bash
   # Create database
   createdb sanctions

   # Or use the provided docker-compose for just PostgreSQL
   docker-compose up -d postgres
   ```

5. **Initialize database**:
   ```bash
   python -m src.scheduler --init-db
   ```

6. **Run update**:
   ```bash
   # One-time update
   python -m src.scheduler --once

   # Or start scheduler for daily updates
   python -m src.scheduler
   ```

## Configuration

Edit `.env` file to configure:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sanctions

# Schedule (daily update time)
UPDATE_SCHEDULE_HOUR=2
UPDATE_SCHEDULE_MINUTE=0
TIMEZONE=UTC

# Logging
LOG_LEVEL=INFO

# Directories
DATA_DIR=data
LOG_DIR=logs
```

## Database Schema

### Tables

- **entities**: Main table for sanctioned individuals/organizations
  - Unique ID, name, type (Individual/Entity)
  - Birth date, place of birth, nationality
  - Passport/national ID numbers
  - Full-text search vector

- **aliases**: Alternative names/AKAs
  - Linked to entities
  - Full-text search enabled

- **addresses**: Entity addresses
  - Structured fields (line1, city, country, postal_code)
  - Full address text

- **sanction_regimes**: Applied sanctions
  - Regime name, type, date imposed

- **update_logs**: Update history
  - Timestamp, status, records added/updated

### Search Features

- Full-text search on entity names and aliases
- PostgreSQL `tsvector` with GIN indexes for performance
- Weighted search (name > title > other fields)

## Usage Examples

### Search by Name

```python
from src.database import SanctionsDatabase

db = SanctionsDatabase('postgresql://user:pass@localhost/sanctions')

# Full-text search
results = db.search("putin")

# Exact name match
results = db.search_by_name("Vladimir Putin", exact=True)

# Partial match
results = db.search_by_name("Vladimir", exact=False)

# Get entity by ID
entity = db.get_entity_by_id("UK-12345")
```

### Get Statistics

```python
from src.database import SanctionsDatabase

db = SanctionsDatabase('postgresql://user:pass@localhost/sanctions')
stats = db.get_stats()

print(f"Total entities: {stats['total_entities']}")
print(f"Individuals: {stats['individuals']}")
print(f"Organizations: {stats['organizations']}")
```

### Manual Update

```python
from src.scheduler import SanctionsScheduler

scheduler = SanctionsScheduler()
success = scheduler.update_sanctions_data()
```

## API Usage

### Starting the API Server

```bash
# Start API server (default: http://0.0.0.0:8000)
python manage.py api

# Start with custom host/port
python manage.py api --host 127.0.0.1 --port 8080

# Start with auto-reload (development)
python manage.py api --reload
```

The API documentation is automatically available at `http://localhost:8000/docs` (Swagger UI).

### API Endpoints

#### 1. Full-Text Search
```bash
GET /api/search?q={query}&limit={limit}

# Example:
curl "http://localhost:8000/api/search?q=Taliban&limit=10"
```

#### 2. Get Entity by ID
```bash
GET /api/entity/{unique_id}

# Example:
curl "http://localhost:8000/api/entity/AFG0001"
```

#### 3. Search by Name
```bash
GET /api/entities?name={name}&exact={true|false}&limit={limit}

# Example (partial match):
curl "http://localhost:8000/api/entities?name=Putin&exact=false&limit=10"

# Example (exact match):
curl "http://localhost:8000/api/entities?name=PUTIN&exact=true"
```

#### 4. Get Statistics
```bash
GET /api/stats

# Example:
curl "http://localhost:8000/api/stats"
```

#### 5. Health Check
```bash
GET /health

# Example:
curl "http://localhost:8000/health"
```

### API Response Format

All search endpoints return JSON in this format:

```json
{
  "query": "Taliban",
  "count": 2,
  "results": [
    {
      "id": 214,
      "unique_id": "AQD0079",
      "entity_type": "Entity",
      "name": "TEHRIK-E TALIBAN PAKISTAN",
      "date_of_birth": null,
      "place_of_birth": "",
      "nationality": "",
      "date_listed": "2011-07-29T00:00:00",
      "last_updated": "2025-10-06T14:24:21.293344",
      "aliases": [
        {
          "alias_type": "Alias",
          "alias_name": "Pakistani Taliban"
        }
      ],
      "addresses": [
        {
          "country": "Afghanistan",
          "full_address": "..."
        }
      ],
      "sanctions": [
        {
          "regime_name": "Isil (Da'esh) and Al-Qaeda...",
          "regime_type": "Asset freeze|Arms embargo",
          "date_imposed": "2011-07-29T00:00:00"
        }
      ]
    }
  ]
}
```

## Testing Individual Components

### Test Downloader
```bash
python -m src.downloader
```

### Test Parser
```bash
# Download a file first, then:
python -m src.parser data/uk_sanctions_list_*.xml
```

### Test Database
```bash
python -m src.database
```

## Data Source

- **Source**: [UK Sanctions List - GOV.UK](https://www.gov.uk/government/publications/the-uk-sanctions-list)
- **Format**: XML (automatically detected and downloaded)
- **Update Frequency**: Daily (or as published)

## Monitoring

### Logs

Logs are written to:
- `logs/sanctions_scheduler.log` - Scheduler and update logs
- Console output for real-time monitoring

### Health Checks

```bash
# Check database stats
python -m src.database

# Check last update
docker-compose logs scheduler | grep "Update completed"
```

## Troubleshooting

### Database Connection Issues
```bash
# Test PostgreSQL connection
psql postgresql://sanctions:sanctions@localhost:5432/sanctions -c "SELECT 1"

# Check Docker network
docker-compose ps
docker-compose logs postgres
```

### Download Failures
- Check internet connectivity
- Verify URL is accessible: https://www.gov.uk/government/publications/the-uk-sanctions-list
- Check logs for detailed error messages

### Parser Issues
- Ensure XML file is valid
- Check parser logs for specific errors
- The parser supports multiple XML schema formats

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
flake8 src/
```

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues and questions, please [open an issue](https://github.com/your-repo/issues).
