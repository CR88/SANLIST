#!/usr/bin/env python
"""
Management script for UK Sanctions Bot
Provides easy commands for common operations
"""
import sys
import argparse
from src.scheduler import SanctionsScheduler, setup_logging
from src.config import Config


def main():
    parser = argparse.ArgumentParser(
        description='UK Sanctions List Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage.py init       # Initialize database
  python manage.py update     # Run one-time update
  python manage.py run        # Start scheduler (daily updates)
  python manage.py stats      # Show database statistics
  python manage.py search "putin"  # Search for entities
  python manage.py api        # Start API server
  python manage.py api --reload  # Start API with auto-reload (dev)
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Init command
    subparsers.add_parser('init', help='Initialize database tables')

    # Update command
    subparsers.add_parser('update', help='Run one-time update')

    # Run command
    subparsers.add_parser('run', help='Start scheduler for daily updates')

    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search for entities')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Max results (default: 10)')

    # Config command
    subparsers.add_parser('config', help='Show current configuration')

    # API command
    api_parser = subparsers.add_parser('api', help='Start API server')
    api_parser.add_argument('--host', default=None, help='Host to bind to (default: from config)')
    api_parser.add_argument('--port', type=int, default=None, help='Port to bind to (default: from config)')
    api_parser.add_argument('--reload', action='store_true', help='Enable auto-reload for development')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Setup logging
    setup_logging()

    # Execute command
    scheduler = SanctionsScheduler()

    if args.command == 'init':
        print("Initializing database...")
        scheduler.database.create_tables()
        print("✓ Database initialized successfully")

    elif args.command == 'update':
        print("Running one-time update...")
        success = scheduler.run_once()
        sys.exit(0 if success else 1)

    elif args.command == 'run':
        print("Starting scheduler...")
        scheduler.run_scheduler()

    elif args.command == 'stats':
        stats = scheduler.database.get_stats()
        print("\n" + "="*50)
        print("Database Statistics")
        print("="*50)
        print(f"Total Entities:    {stats['total_entities']:,}")
        print(f"  Individuals:     {stats['individuals']:,}")
        print(f"  Organizations:   {stats['organizations']:,}")
        print(f"Total Aliases:     {stats['total_aliases']:,}")
        print(f"Last Update:       {stats['last_update']}")
        print("="*50 + "\n")

    elif args.command == 'search':
        results = scheduler.database.search(args.query, limit=args.limit)
        print(f"\nSearch results for '{args.query}' ({len(results)} found):\n")

        for i, entity in enumerate(results, 1):
            print(f"{i}. {entity.name}")
            print(f"   Type: {entity.entity_type}")
            print(f"   ID: {entity.unique_id}")
            if entity.aliases:
                aliases = [a.alias_name for a in entity.aliases[:3]]
                print(f"   Aliases: {', '.join(aliases)}")
            if entity.sanctions:
                regimes = [s.regime_name for s in entity.sanctions[:2]]
                print(f"   Regimes: {', '.join(regimes)}")
            print()

    elif args.command == 'config':
        Config.print_config()

    elif args.command == 'api':
        import uvicorn
        from src.api import app

        host = args.host or Config.API_HOST
        port = args.port or Config.API_PORT

        print(f"Starting API server at http://{host}:{port}")
        print(f"API documentation available at http://{host}:{port}/docs")
        print("Press Ctrl+C to stop\n")

        uvicorn.run(
            "src.api:app",
            host=host,
            port=port,
            reload=args.reload,
            log_level="info"
        )


if __name__ == "__main__":
    main()
