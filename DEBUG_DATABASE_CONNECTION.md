# Debug: Database Not Getting Unsent Emails After Configuration Change

## Problem
After changing the database configuration in `.env`, the service is not fetching unsent emails from the new database.

## Root Cause
Systemd services load environment variables only at startup. When you modify the `.env` file, running services continue using the old configuration until they are restarted.

## Solution Steps

### Step 1: Verify .env File on Server

```bash
# Check current database configuration
cd /opt/sababisha-celery
cat .env | grep MSSQL

# Should show your NEW database settings without quotes:
# MSSQL_SERVER=your-new-server
# MSSQL_DATABASE=your-new-database
# MSSQL_USERNAME=your-new-username
# MSSQL_PASSWORD=your-new-password
# MSSQL_PORT=1418
```

**CRITICAL**: Ensure NO quotes around values for systemd compatibility:
- ✗ Wrong: `MSSQL_DATABASE="new_database"`
- ✓ Correct: `MSSQL_DATABASE=new_database`

### Step 2: Restart Services to Load New Configuration

```bash
# Reload systemd daemon (if service files changed)
sudo systemctl daemon-reload

# Restart ALL services to pick up new .env
sudo systemctl restart sababisha-celery.target

# Verify services restarted successfully
sudo systemctl status sababisha-celery-*
```

### Step 3: Verify Services Are Using New Database

```bash
# Check beat scheduler logs (should show it's querying new database)
sudo journalctl -u sababisha-celery-beat -f

# You should see logs like:
# "Found X unsent emails to process"
# "Queued email ID: XXXX for sending"
```

### Step 4: Manually Test Database Connection

Test if the new database is accessible and has unsent emails:

```bash
cd /opt/sababisha-celery
source venv/bin/activate

# Load .env manually
export $(cat .env | grep -v '^#' | xargs)

# Test connection and query unsent emails
python3 << 'EOF'
from sqlalchemy import create_engine, text
import urllib.parse
import os

# Get credentials from environment
server = os.getenv('MSSQL_SERVER')
database = os.getenv('MSSQL_DATABASE')
username = os.getenv('MSSQL_USERNAME')
password = os.getenv('MSSQL_PASSWORD')
port = os.getenv('MSSQL_PORT', '1433')

print(f"Connecting to: {server}:{port}/{database} as {username}")

# URL encode password
encoded_password = urllib.parse.quote_plus(password)

# Create connection string
conn_str = f"mssql+pymssql://{username}:{encoded_password}@{server}:{port}/{database}"

try:
    # Create engine and connect
    engine = create_engine(conn_str)
    with engine.connect() as conn:
        # Check if emailmessages table exists
        result = conn.execute(text("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_NAME = 'emailmessages'
        """))

        if result.rowcount == 0:
            print("❌ ERROR: emailmessages table does NOT exist in this database!")
        else:
            print("✓ emailmessages table found")

            # Count unsent emails
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM emailmessages
                WHERE statusflag = 0
            """))
            count = result.scalar()
            print(f"✓ Found {count} unsent emails (statusflag=0)")

            # Show sample unsent email IDs
            result = conn.execute(text("""
                SELECT TOP 5 messageid, recipient, subject, statusflag, status
                FROM emailmessages
                WHERE statusflag = 0
                ORDER BY messageid
            """))

            print("\nSample unsent emails:")
            for row in result:
                print(f"  - ID: {row[0]}, To: {row[1]}, Subject: {row[2]}, Status: {row[4]}")

except Exception as e:
    print(f"❌ Connection failed: {e}")
EOF
```

### Step 5: Check Worker Logs

```bash
# Check if workers are processing tasks
sudo journalctl -u sababisha-celery-worker -f

# You should see:
# "Received task: tasks.send_email"
# "Email sent successfully to: ..."
# "Marked email XXXX as sent"
```

## Common Issues and Fixes

### Issue 1: Services Still Using Old Database

**Symptom**: Logs show old database name or connection errors to old server

**Fix**:
```bash
# Force kill all celery processes
sudo pkill -9 celery

# Restart services
sudo systemctl restart sababisha-celery.target

# Verify processes are new
ps aux | grep celery
```

### Issue 2: Table 'emailmessages' Doesn't Exist in New Database

**Symptom**: Error: `Invalid object name 'emailmessages'`

**Fix**: Ensure the new database has the correct schema. Check table name:
```bash
cd /opt/sababisha-celery
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)

python3 << 'EOF'
from sqlalchemy import create_engine, text
import urllib.parse
import os

server = os.getenv('MSSQL_SERVER')
database = os.getenv('MSSQL_DATABASE')
username = os.getenv('MSSQL_USERNAME')
password = os.getenv('MSSQL_PASSWORD')
port = os.getenv('MSSQL_PORT', '1433')

encoded_password = urllib.parse.quote_plus(password)
conn_str = f"mssql+pymssql://{username}:{encoded_password}@{server}:{port}/{database}"

engine = create_engine(conn_str)
with engine.connect() as conn:
    # List all tables
    result = conn.execute(text("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """))

    print("Available tables in database:")
    for row in result:
        print(f"  - {row[0]}")
EOF
```

### Issue 3: Wrong Database Credentials

**Symptom**: `Login failed for user 'username'`

**Fix**: Verify credentials in .env match the new database:
```bash
# Test credentials directly
cd /opt/sababisha-celery
source venv/bin/activate

python3 << EOF
import pymssql
import os

# Load .env
with open('.env') as f:
    for line in f:
        if line.strip() and not line.startswith('#') and '=' in line:
            key, value = line.strip().split('=', 1)
            os.environ[key] = value

server = os.getenv('MSSQL_SERVER')
database = os.getenv('MSSQL_DATABASE')
username = os.getenv('MSSQL_USERNAME')
password = os.getenv('MSSQL_PASSWORD')
port = int(os.getenv('MSSQL_PORT', '1433'))

print(f"Testing: {username}@{server}:{port}/{database}")

try:
    conn = pymssql.connect(
        server=server,
        user=username,
        password=password,
        database=database,
        port=port
    )
    print("✓ Connection successful!")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
EOF
```

### Issue 4: No Unsent Emails in New Database

**Symptom**: Connection works but no emails are sent

**Fix**: Verify there are actually unsent emails (statusflag=0):
```sql
-- Run this query on your NEW database
SELECT
    COUNT(*) as total_emails,
    SUM(CASE WHEN statusflag = 0 THEN 1 ELSE 0 END) as unsent,
    SUM(CASE WHEN statusflag = 1 THEN 1 ELSE 0 END) as sent
FROM emailmessages;
```

If unsent count is 0, insert a test email:
```sql
INSERT INTO emailmessages (
    recipient, subject, body, sender,
    statusflag, status, encrypted, password
) VALUES (
    'test@example.com',
    'Test Email',
    'This is a test email body',
    'Sababisha',
    0,  -- unsent
    'PENDING',
    0,  -- not encrypted
    NULL
);
```

## Verification Checklist

After making changes, verify:

- [ ] `.env` file has NO quotes around values
- [ ] `.env` file has correct new database credentials
- [ ] Services have been restarted: `sudo systemctl restart sababisha-celery.target`
- [ ] All services are active: `sudo systemctl status sababisha-celery-*`
- [ ] Beat scheduler is running: `sudo journalctl -u sababisha-celery-beat -f`
- [ ] Workers are active: `sudo journalctl -u sababisha-celery-worker -f`
- [ ] Database connection test succeeds (see Step 4 above)
- [ ] New database has `emailmessages` table
- [ ] New database has unsent emails (statusflag=0)
- [ ] Logs show "Found X unsent emails" from beat scheduler

## Quick Debug Commands

```bash
# One-liner to check everything
cd /opt/sababisha-celery && \
echo "=== .env Database Config ===" && \
grep MSSQL .env && \
echo -e "\n=== Service Status ===" && \
sudo systemctl is-active sababisha-celery-beat sababisha-celery-worker && \
echo -e "\n=== Recent Beat Logs ===" && \
sudo journalctl -u sababisha-celery-beat -n 20 --no-pager && \
echo -e "\n=== Recent Worker Logs ===" && \
sudo journalctl -u sababisha-celery-worker -n 20 --no-pager
```

## Still Not Working?

If after all these steps it's still not working, collect debug info:

```bash
# Generate debug report
cd /opt/sababisha-celery

cat > debug_report.txt << 'DEBUG'
=== Environment Configuration ===
$(cat .env | grep MSSQL)

=== Service Status ===
$(sudo systemctl status sababisha-celery-beat --no-pager)
$(sudo systemctl status sababisha-celery-worker --no-pager)

=== Beat Logs (Last 50 lines) ===
$(sudo journalctl -u sababisha-celery-beat -n 50 --no-pager)

=== Worker Logs (Last 50 lines) ===
$(sudo journalctl -u sababisha-celery-worker -n 50 --no-pager)

=== Running Celery Processes ===
$(ps aux | grep celery)

=== Database Connection Test ===
$(python3 -c "
from sqlalchemy import create_engine, text
import urllib.parse
import os

# Load env
with open('.env') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            k, v = line.strip().split('=', 1)
            os.environ[k] = v

server = os.getenv('MSSQL_SERVER')
database = os.getenv('MSSQL_DATABASE')
username = os.getenv('MSSQL_USERNAME')
password = os.getenv('MSSQL_PASSWORD')
port = os.getenv('MSSQL_PORT')

encoded_password = urllib.parse.quote_plus(password)
conn_str = f'mssql+pymssql://{username}:{encoded_password}@{server}:{port}/{database}'

try:
    engine = create_engine(conn_str)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM emailmessages WHERE statusflag = 0'))
        print(f'Unsent emails: {result.scalar()}')
except Exception as e:
    print(f'Error: {e}')
")
DEBUG

cat debug_report.txt
```

Share the debug report for further assistance.

---

**Contact Support:**
- Developer: Civious Rumaita
- Phone: 0715088150
