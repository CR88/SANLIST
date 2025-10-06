#!/usr/bin/env python3
"""
Railway startup script
Initializes database and starts the API server
"""
import os
import sys
import logging
from src.config import Config
from src.database import SanctionsDatabase

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize database tables if they don't exist"""
    try:
        logger.info("Checking database initialization...")
        db = SanctionsDatabase(Config.DATABASE_URL)

        # Create tables (will skip if already exist)
        db.create_tables()
        logger.info("✓ Database tables ready")

        # Check if database is empty
        stats = db.get_stats()
        if stats['total_entities'] == 0:
            logger.info("Database is empty. Run initial data update with:")
            logger.info("  python manage.py update")
            logger.info("Or the scheduler will update automatically at scheduled time")
        else:
            logger.info(f"✓ Database has {stats['total_entities']} entities")

        return True
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False


def start_api_server():
    """Start the FastAPI server"""
    try:
        import uvicorn
        from src.api import app

        host = Config.API_HOST
        port = Config.API_PORT

        logger.info(f"Starting API server on {host}:{port}")
        logger.info(f"API documentation: http://{host}:{port}/docs")
        logger.info(f"Web interface: http://{host}:{port}/static/index.html")

        # Start server
        uvicorn.run(
            "src.api:app",
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start API server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("UK Sanctions List Bot - Railway Startup")
    logger.info("=" * 60)

    # Initialize database
    if not initialize_database():
        logger.error("Failed to initialize database. Exiting.")
        sys.exit(1)

    # Start API server
    start_api_server()
