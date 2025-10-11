import os
import sys
import logging
from datetime import datetime
import time
from dotenv import load_dotenv
from sqlalchemy import text
from celery_config import app
from tracing import setup_tracing

# Load environment variables
load_dotenv()
setup_tracing()
# Configure logging
from loki_loghandler import logger

def test_redis_connection():
    """Test Redis connection with password authentication"""
    try:
        import redis
        from celery import Celery
        
        # Get Redis configuration from environment
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD', '')
        redis_db = int(os.getenv('REDIS_DB', 0))
        
        # Construct Redis URL with password
        if redis_password:
            redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        else:
            redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
        
        # Mask password for logging
        logged_url = redis_url.replace(f":{redis_password}@", ":***@") if redis_password else redis_url
        logger.info(f"Testing Redis connection to: {logged_url}")
        
        # Test 1: Direct Redis connection with authentication
        logger.info("Testing direct Redis connection...")
        try:
            if redis_password:
                r = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_password,
                    db=redis_db,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
            else:
                r = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
            
            # Test connection
            if r.ping():
                logger.info("✅ Direct Redis connection successful")
            else:
                logger.error("❌ Direct Redis ping failed")
                return False
                
        except redis.AuthenticationError as e:
            logger.error(f"❌ Redis authentication failed: {e}")
            return False
        except redis.ConnectionError as e:
            logger.error(f"❌ Redis connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Direct Redis connection failed: {e}")
            return False
        
        # Test 2: Celery broker connection
        logger.info("Testing Celery broker connection...")
        try:
            test_app = app
            
            
            with test_app.connection() as conn:
                conn.ensure_connection(max_retries=3)
                logger.info("✅ Celery broker connection successful")
                
        except Exception as e:
            logger.error(f"❌ Celery broker connection failed: {e}")
            return False
        
        # Test 3: Test actual task queueing
        logger.info("Testing Celery task submission...")
        try:
            @test_app.task
            def test_task():
                return "success"
            
            # Submit a test task
            result = test_task.apply_async()
            task_result = result.get(timeout=10)
            if task_result == "success":
                logger.info("✅ Celery task execution successful")
            else:
                logger.error("❌ Celery task execution failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Celery task test failed: {e}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Redis connection test failed: {e}")
        return False

def test_database_connection():
    """Test MSSQL database connection"""
    try:
        from database import SessionLocal, engine
        
        logger.info("Testing database connection...")
        db = SessionLocal()

        # Test if OutEmail table exists and has data
        try:
            from models import OutEmail
            with SessionLocal() as db:
                count = db.execute(text("SELECT COUNT(*) FROM OutEmail")).scalar()
                logger.info(f"✅ OutEmail table exists with {count} records")
        except Exception as e:
            logger.warning(f"OutEmail table might not exist or has issues: {e}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False

def test_unsent_emails_query():
    """Test the unsent emails query"""
    try:
        from email_tasks import get_unsent_messages
        
        logger.info("Testing unsent emails query...")
        emails = get_unsent_messages()
        logger.info(f"✅ Unsent emails query successful. Found {len(emails)} emails")
        
        if emails:
            for i, email in enumerate(emails[:3]):  # Show first 3 emails
                logger.info(f"  {i+1}. ID: {email['id']}, To: {email['email']}, Retries: {email['retries']}")
                logger.info(f"     Subject: {email['subject'][:50]}...")
        else:
            logger.info("  No unsent emails found")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Unsent emails query failed: {e}")
        return False

def test_celery_task_submission():
    """Test submitting actual tasks to Celery"""
    try:
        from email_tasks import app, log_error
        
        logger.info("Testing Celery task submission...")
        
        # Test error logging task
        test_error_data = {
            'error': 'Test error from debug script - ' + datetime.now().isoformat(),
            'service': 'DebugService',
            'source': 'DebugScript',
            'occured_at': datetime.now().isoformat()
        }
        
        # Submit task to log queue
        test_task = log_error.apply_async(
            args=[test_error_data],
            queue='log-queue'
        )
        
        # Wait for result with timeout
        try:
            result = test_task.get(timeout=10)
            logger.info(f"✅ Log task completed successfully")
        except Exception as e:
            logger.error(f"❌ Log task failed or timed out: {e}")
            return False
        
        # Test if we can submit to the email queue (without waiting for completion)
        from email_tasks import scrape_unsent_emails
        email_task = scrape_unsent_emails.apply_async(queue='datagemail-queue')
        logger.info(f"✅ Email task submitted successfully: {email_task.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Celery task submission test failed: {e}")
        return False

def test_email_sending_dry_run():
    """Test email sending without actually sending emails"""
    try:
        logger.info("Testing email sending (dry run)...")
        
        # Mock SMTP connection test
        import smtplib
        try:
            # Just test connection, don't send
            with smtplib.SMTP_SSL('mail.datag.co.ke', 465) as server:
                logger.info("✅ SMTP connection test successful")
        except Exception as e:
            logger.warning(f"SMTP connection test failed (might be expected): {e}")
        
        # Test email composition
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        
        test_msg = MIMEMultipart()
        test_msg['From'] = 'datag@datag.co.ke'
        test_msg['To'] = 'koriojohn59@gmail.com'
        test_msg['Subject'] = 'Test Email'
        
        logger.info("✅ Email composition test successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Email sending dry run failed: {e}")
        return False

def check_environment_config():
    """Check if all required environment variables are set"""
    logger.info("Checking environment configuration...")
    
    required_vars = {
        'REDIS_HOST': os.getenv('REDIS_HOST', 'localhost'),
        'REDIS_PORT': os.getenv('REDIS_PORT', '6379'),
        'REDIS_PASSWORD': '***' if os.getenv('REDIS_PASSWORD') else 'Not set',
        'MSSQL_SERVER': os.getenv('MSSQL_SERVER'),
        'MSSQL_DATABASE': os.getenv('MSSQL_DATABASE'),
        'MSSQL_USERNAME': os.getenv('MSSQL_USERNAME'),
        'MSSQL_PASSWORD': '***' if os.getenv('MSSQL_PASSWORD') else 'Not set',
    }
    
    missing_vars = []
    for var, value in required_vars.items():
        if value is None or value == 'Not set':
            missing_vars.append(var)
        else:
            logger.info(f"  ✅ {var}: {value}")
    
    if missing_vars:
        logger.error("❌ Missing required environment variables:")
        for var in missing_vars:
            logger.error(f"    - {var}")
        return False
    
    logger.info("✅ All environment variables are set")
    return True

def run_interactive_debugger():
    """Start an interactive debugger session"""
    try:
        import pdb
        print("\n" + "="*50)
        print("STARTING INTERACTIVE DEBUGGER")
        print("="*50)
        print("Available variables in debugger:")
        print("  - test_redis_connection()")
        print("  - test_database_connection()") 
        print("  - test_unsent_emails_query()")
        print("  - test_celery_task_submission()")
        print("  - test_email_sending_dry_run()")
        print("\nType 'c' to continue or use debugger commands")
        print("="*50)
        
        # Set a breakpoint for interactive debugging
        pdb.set_trace()
        
    except Exception as e:
        logger.error(f"Debugger failed: {e}")

def main():
    """Main test function"""
    print("🔧 Celery Email Service - Pre-deployment Tests")
    print("=" * 60)
    
    # First check environment configuration
    if not check_environment_config():
        print("❌ Environment configuration check failed. Please check your .env file")
        return
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Database Connection", test_database_connection),
        ("Unsent Emails Query", test_unsent_emails_query),
        ("Celery Task Submission", test_celery_task_submission),
        ("Email Sending Dry Run", test_email_sending_dry_run),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"Running {test_name}...")
        try:
            success = test_func()
            results.append((test_name, success))
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
        except Exception as e:
            results.append((test_name, False))
            print(f"❌ FAIL {test_name} - Exception: {e}")
        
        time.sleep(1)  # Small delay between tests
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY:")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! You can start Celery workers.")
        print("\nTo start workers, run:")
        print("  celery -A email_tasks worker --queues=datagemail-queue --concurrency=4 --loglevel=info")
        print("  celery -A email_tasks worker --queues=log-queue --concurrency=2 --loglevel=info") 
        print("  celery -A email_tasks beat --loglevel=info")
    else:
        print("❌ Some tests failed. Please check the logs above.")
        print("\nFailed tests:")
        for test_name, success in results:
            if not success:
                print(f"  - {test_name}")
    
    # Ask if user wants to start interactive debugger
    response = input("\nStart interactive debugger? (y/n): ")
    if response.lower() == 'y':
        run_interactive_debugger()

if __name__ == "__main__":
    main()