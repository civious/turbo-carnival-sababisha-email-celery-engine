#!/usr/bin/env python3
"""
Test database connection and check for unsent emails
Run this on the server to verify database connectivity
"""

from sqlalchemy import create_engine, text
import urllib.parse
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Get credentials from environment
server = os.getenv('MSSQL_SERVER')
database = os.getenv('MSSQL_DATABASE')
username = os.getenv('MSSQL_USERNAME')
password = os.getenv('MSSQL_PASSWORD')
port = os.getenv('MSSQL_PORT', '1418')  # Default to 1418

print("=" * 60)
print("Database Connection Test")
print("=" * 60)
print(f"Server:   {server}:{port}")
print(f"Database: {database}")
print(f"Username: {username}")
print(f"Password: {'*' * len(password) if password else '(empty)'}")
print("=" * 60)
print()

# URL encode password to handle special characters
encoded_password = urllib.parse.quote_plus(password)

# Create connection string
conn_str = f"mssql+pymssql://{username}:{encoded_password}@{server}:{port}/{database}"

try:
    # Create engine and connect
    print("Creating database engine...")
    engine = create_engine(conn_str, pool_pre_ping=True)

    print("Attempting connection...")
    with engine.connect() as conn:
        print("✓ Connection successful!")
        print()

        # Check if emailmessages table exists
        print("Checking for emailmessages table...")
        result = conn.execute(text("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'emailmessages'
        """))

        table_exists = result.fetchone()

        if not table_exists:
            print("❌ ERROR: emailmessages table does NOT exist in this database!")
            print()
            print("Available tables:")
            result = conn.execute(text("""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """))
            for row in result:
                print(f"  - {row[0]}")
        else:
            print("✓ emailmessages table found")
            print()

            # Count total emails
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM emailmessages
            """))
            total_count = result.scalar()
            print(f"Total emails in table: {total_count}")

            # Count unsent emails
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM emailmessages
                WHERE statusflag = 0
            """))
            unsent_count = result.scalar()
            print(f"✓ Found {unsent_count} unsent emails (statusflag=0)")

            # Count sent emails
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM emailmessages
                WHERE statusflag = 1
            """))
            sent_count = result.scalar()
            print(f"  Sent emails (statusflag=1): {sent_count}")
            print()

            # Show sample unsent email IDs
            if unsent_count > 0:
                print("Sample unsent emails (first 5):")
                result = conn.execute(text("""
                    SELECT TOP 5 messageid, recipient, subject, statusflag, status
                    FROM emailmessages
                    WHERE statusflag = 0
                    ORDER BY messageid
                """))

                for row in result:
                    print(f"  - ID: {row[0]}, To: {row[1]}, Subject: {row[2][:30]}..., Status: {row[4]}")
            else:
                print("⚠ No unsent emails found!")
                print()
                print("To insert a test email, run:")
                print("""
INSERT INTO emailmessages (
    recipient, subject, body, sender,
    statusflag, status, encrypted, password
) VALUES (
    'test@example.com',
    'Test Email',
    'This is a test email body',
    'Sababisha',
    0,
    'PENDING',
    0,
    NULL
);
""")

except Exception as e:
    print(f"❌ Connection failed!")
    print(f"Error: {e}")
    print()
    print("Common issues:")
    print("1. Wrong port (should be 1418, not 1433)")
    print("2. Database server not accessible from this host")
    print("3. Wrong username/password")
    print("4. Firewall blocking connection")
    print("5. Database server is down")

print()
print("=" * 60)
