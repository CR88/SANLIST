"""
Configuration management for UK Sanctions Bot
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """
    Application configuration
    """

    # Database
    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        'postgresql://sanctions:sanctions@localhost:5432/sanctions'
    )

    # Data sources
    SANCTIONS_LIST_URL: str = os.getenv(
        'SANCTIONS_LIST_URL',
        'https://www.gov.uk/government/publications/the-uk-sanctions-list'
    )

    # Directories
    DATA_DIR: str = os.getenv('DATA_DIR', 'data')
    LOG_DIR: str = os.getenv('LOG_DIR', 'logs')

    # Scheduling
    UPDATE_SCHEDULE_HOUR: int = int(os.getenv('UPDATE_SCHEDULE_HOUR', '2'))  # 2 AM
    UPDATE_SCHEDULE_MINUTE: int = int(os.getenv('UPDATE_SCHEDULE_MINUTE', '0'))
    TIMEZONE: str = os.getenv('TIMEZONE', 'UTC')

    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # API (future use)
    API_HOST: str = os.getenv('API_HOST', '0.0.0.0')
    # Railway uses PORT, fallback to API_PORT, then default 8000
    API_PORT: int = int(os.getenv('PORT', os.getenv('API_PORT', '8000')))
    API_WORKERS: int = int(os.getenv('API_WORKERS', '4'))

    # Download settings
    DOWNLOAD_TIMEOUT: int = int(os.getenv('DOWNLOAD_TIMEOUT', '60'))
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '30'))

    # Database connection pool settings
    DB_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', '5'))
    DB_MAX_OVERFLOW: int = int(os.getenv('DB_MAX_OVERFLOW', '10'))

    @classmethod
    def validate(cls) -> bool:
        """
        Validate configuration

        Returns:
            bool: True if valid, False otherwise
        """
        # Check required configurations
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")

        # Create directories if they don't exist
        os.makedirs(cls.DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOG_DIR, exist_ok=True)

        return True

    @classmethod
    def get_database_url(cls, hide_password: bool = False) -> str:
        """
        Get database URL, optionally hiding the password

        Args:
            hide_password: If True, replace password with asterisks

        Returns:
            str: Database URL
        """
        url = cls.DATABASE_URL

        if hide_password and '@' in url:
            # Extract and hide password
            parts = url.split('@')
            if '://' in parts[0] and ':' in parts[0]:
                prefix = parts[0].split('://')[0]
                creds = parts[0].split('://')[1]
                if ':' in creds:
                    user = creds.split(':')[0]
                    url = f"{prefix}://{user}:****@{parts[1]}"

        return url

    @classmethod
    def print_config(cls):
        """
        Print current configuration (for debugging)
        """
        print("=" * 50)
        print("UK Sanctions Bot Configuration")
        print("=" * 50)
        print(f"Database URL: {cls.get_database_url(hide_password=True)}")
        print(f"Data Directory: {cls.DATA_DIR}")
        print(f"Log Directory: {cls.LOG_DIR}")
        print(f"Update Schedule: {cls.UPDATE_SCHEDULE_HOUR:02d}:{cls.UPDATE_SCHEDULE_MINUTE:02d} {cls.TIMEZONE}")
        print(f"Log Level: {cls.LOG_LEVEL}")
        print(f"API Host: {cls.API_HOST}:{cls.API_PORT}")
        print("=" * 50)


# Validate configuration on import
Config.validate()
