#!/usr/bin/env python3
"""
AllôBye Schema Application Script

This script applies the database schema to Supabase and optionally seeds it with sample data.

Usage:
    python apply_schema.py                    # Apply schema only
    python apply_schema.py --seed             # Apply schema and seed data
    python apply_schema.py --seed-only        # Apply seed data only (schema must exist)
    python apply_schema.py --verify           # Verify schema without applying
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(message: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{'═' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'═' * 60}{Colors.ENDC}\n")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓{Colors.ENDC} {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.FAIL}✗{Colors.ENDC} {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.WARNING}⚠{Colors.ENDC} {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.OKCYAN}ℹ{Colors.ENDC} {message}")


def get_database_connection() -> Optional[psycopg2.extensions.connection]:
    """Create a connection to the Supabase database."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print_error("DATABASE_URL not found in environment variables")
        print_info("Make sure .env file exists and contains DATABASE_URL")
        return None

    try:
        print_info("Connecting to Supabase database...")
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        print_success("Connected to database successfully")
        return conn
    except psycopg2.Error as e:
        print_error(f"Database connection failed: {e}")
        return None


def read_sql_file(file_path: Path) -> Optional[str]:
    """Read SQL file content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print_success(f"Read {file_path.name} ({len(content)} bytes)")
        return content
    except FileNotFoundError:
        print_error(f"File not found: {file_path}")
        return None
    except Exception as e:
        print_error(f"Error reading {file_path}: {e}")
        return None


def execute_sql(conn: psycopg2.extensions.connection, sql_content: str, description: str) -> bool:
    """Execute SQL content and handle errors."""
    try:
        cursor = conn.cursor()
        print_info(f"Executing {description}...")

        # Execute the SQL
        cursor.execute(sql_content)

        # Try to get any NOTICE messages (like from seed.sql)
        for notice in conn.notices:
            print(notice.strip())
        conn.notices.clear()

        cursor.close()
        print_success(f"{description} completed successfully")
        return True
    except psycopg2.Error as e:
        print_error(f"Error executing {description}:")
        print_error(f"  {e}")
        return False


def verify_schema(conn: psycopg2.extensions.connection) -> bool:
    """Verify that the schema was applied correctly."""
    print_info("Verifying schema...")

    expected_tables = [
        'schools',
        'children',
        'delegates',
        'pickups',
        'pickup_children',
        'delegate_children',
        'emergencies',
        'schema_version'
    ]

    try:
        cursor = conn.cursor()

        # Check if all expected tables exist
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        existing_tables = [row[0] for row in cursor.fetchall()]

        # Check which tables are present
        missing_tables = set(expected_tables) - set(existing_tables)
        extra_tables = set(existing_tables) - set(expected_tables)

        if missing_tables:
            print_warning(f"Missing tables: {', '.join(missing_tables)}")

        if extra_tables:
            print_info(f"Additional tables: {', '.join(extra_tables)}")

        # Count records in each table
        print(f"\n{Colors.BOLD}Table Summary:{Colors.ENDC}")
        for table in sorted(existing_tables):
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
            count = cursor.fetchone()[0]
            print(f"  {table:20} {count:>6} rows")

        # Check schema version
        if 'schema_version' in existing_tables:
            cursor.execute("SELECT version, description, applied_at FROM schema_version ORDER BY version DESC LIMIT 1")
            version_info = cursor.fetchone()
            if version_info:
                print(f"\n{Colors.BOLD}Schema Version:{Colors.ENDC}")
                print(f"  Version:     {version_info[0]}")
                print(f"  Description: {version_info[1]}")
                print(f"  Applied:     {version_info[2]}")

        cursor.close()

        if not missing_tables:
            print_success("Schema verification passed")
            return True
        else:
            print_warning("Schema verification completed with warnings")
            return False

    except psycopg2.Error as e:
        print_error(f"Error verifying schema: {e}")
        return False


def apply_schema(conn: psycopg2.extensions.connection, schema_file: Path) -> bool:
    """Apply the database schema."""
    print_header("Applying Database Schema")

    sql_content = read_sql_file(schema_file)
    if not sql_content:
        return False

    return execute_sql(conn, sql_content, "schema migration")


def apply_seed(conn: psycopg2.extensions.connection, seed_file: Path) -> bool:
    """Apply seed data."""
    print_header("Applying Seed Data")

    sql_content = read_sql_file(seed_file)
    if not sql_content:
        return False

    return execute_sql(conn, sql_content, "seed data")


def enable_realtime(conn: psycopg2.extensions.connection) -> bool:
    """Enable real-time replication for specific tables."""
    print_header("Enabling Real-time Replication")

    realtime_tables = ['pickups', 'emergencies', 'pickup_children']

    try:
        cursor = conn.cursor()

        for table in realtime_tables:
            print_info(f"Enabling real-time for {table}...")

            # Check if publication exists
            cursor.execute("""
                SELECT COUNT(*)
                FROM pg_publication
                WHERE pubname = 'supabase_realtime'
            """)

            if cursor.fetchone()[0] == 0:
                print_warning("supabase_realtime publication does not exist")
                print_info("You may need to enable this in the Supabase dashboard")
                cursor.close()
                return False

            # Add table to publication
            try:
                cursor.execute(
                    sql.SQL("ALTER PUBLICATION supabase_realtime ADD TABLE {}").format(
                        sql.Identifier(table)
                    )
                )
                print_success(f"Enabled real-time for {table}")
            except psycopg2.Error as e:
                if "already a member" in str(e):
                    print_info(f"Real-time already enabled for {table}")
                else:
                    raise

        cursor.close()
        return True

    except psycopg2.Error as e:
        print_error(f"Error enabling real-time: {e}")
        print_warning("You may need to enable real-time in the Supabase dashboard manually")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Apply AllôBye database schema to Supabase',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Apply schema only
  %(prog)s --seed             Apply schema and seed data
  %(prog)s --seed-only        Apply seed data only
  %(prog)s --verify           Verify schema without applying
  %(prog)s --enable-realtime  Enable real-time for tables
        """
    )

    parser.add_argument(
        '--seed',
        action='store_true',
        help='Apply seed data after schema'
    )

    parser.add_argument(
        '--seed-only',
        action='store_true',
        help='Apply seed data only (schema must already exist)'
    )

    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify schema without applying'
    )

    parser.add_argument(
        '--enable-realtime',
        action='store_true',
        help='Enable real-time replication for tables'
    )

    args = parser.parse_args()

    # Load environment variables
    script_dir = Path(__file__).parent
    env_file = script_dir / '.env'

    if not env_file.exists():
        print_error(f".env file not found at {env_file}")
        print_info("Create a .env file with your Supabase credentials")
        sys.exit(1)

    load_dotenv(env_file)

    # Define file paths
    schema_file = script_dir / 'schema.sql'
    seed_file = script_dir / 'seed.sql'

    # Connect to database
    conn = get_database_connection()
    if not conn:
        sys.exit(1)

    try:
        success = True

        # Apply schema
        if not args.seed_only and not args.verify and not args.enable_realtime:
            if not apply_schema(conn, schema_file):
                success = False

        # Apply seed data
        if args.seed or args.seed_only:
            if not apply_seed(conn, seed_file):
                success = False

        # Enable real-time
        if args.enable_realtime:
            if not enable_realtime(conn):
                success = False

        # Verify schema
        if args.verify or success:
            verify_schema(conn)

        if success:
            print_header("✓ All operations completed successfully!")
        else:
            print_header("⚠ Some operations failed")
            sys.exit(1)

    finally:
        conn.close()
        print_info("Database connection closed")


if __name__ == '__main__':
    main()
