#!/usr/bin/env python3
"""
Celery Debugging Script
Run this to check your Celery setup
"""
import os
import sys
import redis
from dotenv import load_dotenv

# Add current directory to path
sys.path.insert(0, '.')

# Load environment
load_dotenv()

print("=" * 60)
print("CELERY DEBUGGING TOOL")
print("=" * 60)

# 1. Check Redis Connection
print("\n1. REDIS CONNECTION:")
print("-" * 40)
try:
    r = redis.Redis(
        host=os.getenv('REDIS_HOST'),
        port=int(os.getenv('REDIS_PORT')),
        password=os.getenv('REDIS_PASSWORD', ''),
        decode_responses=True
    )
    r.ping()
    print("✅ Redis connected successfully")
    print(f"   Host: {os.getenv('REDIS_HOST')}")
    print(f"   Port: {os.getenv('REDIS_PORT')}")
except Exception as e:
    print(f"❌ Redis connection failed: {e}")
    sys.exit(1)

# 2. Check Queue Status
print("\n2. QUEUE STATUS:")
print("-" * 40)
queues = ['celery', 'datagemail-queue', 'log-queue']
for queue_name in queues:
    length = r.llen(queue_name)
    status = "✅" if length == 0 or queue_name == 'celery' else "⚠️"
    print(f"{status} {queue_name}: {length} tasks")

# 3. Check Celery Configuration
print("\n3. CELERY CONFIGURATION:")
print("-" * 40)
try:
    from celery_config import app
    print(f"✅ Celery app loaded: {app.main}")
    print(f"   Broker: {app.conf.broker_url[:50]}...")
    print(f"   Backend: {app.conf.result_backend[:50]}...")
    print(f"   Beat schedule: {list(app.conf.beat_schedule.keys())}")
except Exception as e:
    print(f"❌ Failed to load Celery config: {e}")

# 4. Check Workers
print("\n4. WORKER STATUS:")
print("-" * 40)
try:
    inspector = app.control.inspect()

    # Ping workers
    pong = inspector.ping()
    if pong:
        print(f"✅ Workers online: {len(pong)}")
        for worker_name in pong.keys():
            print(f"   - {worker_name}")
    else:
        print("❌ No workers responding")

    # Check registered tasks
    registered = inspector.registered()
    if registered:
        for worker, tasks in registered.items():
            print(f"\n   Worker: {worker}")
            print(f"   Registered tasks: {len(tasks)}")
            for task in sorted(tasks):
                if 'tasks.' in task:
                    print(f"      - {task}")

    # Check active queues
    active_queues = inspector.active_queues()
    if active_queues:
        print(f"\n   Active queues:")
        for worker, queues in active_queues.items():
            for queue in queues:
                print(f"      - {queue['name']}")

except Exception as e:
    print(f"❌ Failed to inspect workers: {e}")

# 5. Check Database
print("\n5. DATABASE CONNECTION:")
print("-" * 40)
try:
    from database import SessionLocal
    db = SessionLocal()
    print("✅ Database connected successfully")
    db.close()
except Exception as e:
    print(f"❌ Database connection failed: {e}")

# 6. Check Tasks Module
print("\n6. TASKS MODULE:")
print("-" * 40)
try:
    from tasks import scrape_unsent_emails, send_email, get_unsent_messages
    print("✅ Tasks module loaded successfully")
    print("   Available tasks:")
    print("   - scrape_unsent_emails")
    print("   - send_email")
    print("   - get_unsent_messages")

    # Test getting emails
    emails = get_unsent_messages()
    print(f"\n   📧 Unsent emails in database: {len(emails)}")
    if emails:
        print(f"   First email ID: {emails[0]['id']}")
        print(f"   Recipient: {emails[0]['recipient']}")

except Exception as e:
    print(f"❌ Failed to load tasks: {e}")
    import traceback
    traceback.print_exc()

# 7. Check Encryption
print("\n7. ENCRYPTION:")
print("-" * 40)
encryption_key = os.getenv('ENCRYPTION_KEY', '')
if encryption_key:
    print(f"✅ Encryption key set ({len(encryption_key)} chars)")
else:
    print("❌ No encryption key set")

# 8. Summary
print("\n" + "=" * 60)
print("SUMMARY:")
print("-" * 40)

issues = []
if r.llen('datagemail-queue') > 0:
    issues.append(f"⚠️  {r.llen('datagemail-queue')} tasks stuck in datagemail-queue")

if not pong:
    issues.append("❌ No workers online")

if issues:
    print("\nISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")
    print("\nRECOMMENDATIONS:")
    if r.llen('datagemail-queue') > 0:
        print("  1. Delete celerybeat-schedule file")
        print("  2. Restart beat scheduler")
        print("  3. Workers should pick up tasks from 'celery' queue")
    if not pong:
        print("  1. Start workers: ./venv/bin/celery -A celery_config:app worker --loglevel=info")
else:
    print("✅ No issues detected! System looks good.")

print("=" * 60)
