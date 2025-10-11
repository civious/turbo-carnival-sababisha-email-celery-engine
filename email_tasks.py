from celery import current_task
from celery.exceptions import MaxRetriesExceededError
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
import os
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import app from celery_config
from celery_config import app

# Import safe observability
from loki_loghandler import logger
from profiling import profile_task
from tracing import get_tracer, trace_task
from database import SessionLocal
from models import OutEmail, ErrorLogs

# Database functions
def get_unsent_messages():
    """Get unsent emails from database"""
    try:
        db = SessionLocal()
        query = text("""
            SELECT id, email, subject, msg, hasfile, filetobesent, documentname, retries
            FROM OutEmail 
            WHERE is_sent = 0 AND retries < 3
        """)
        
        result = db.execute(query)
        emails = []
        for row in result:
            emails.append({
                'id': row.id,
                'email': row.email,
                'subject': row.subject,
                'msg': row.msg,
                'has_file': row.hasfile,
                'file_to_be_sent': row.filetobesent,
                'document_name': row.documentname,
                'retries': row.retries
            })
        
        return emails
    except Exception as e:
        logger.error(f"Error fetching unsent messages: {e}")
        return []
    finally:
        db.close()

def mark_sent(email_id: int):
    """Mark email as sent"""
    try:
        db = SessionLocal()
        db.execute(
            text("UPDATE OutEmail SET is_sent = 1 WHERE id = :id"),
            {'id': email_id}
        )
        db.commit()
    except Exception as e:
        logger.error(f"Error marking email {email_id} as sent: {e}")
        db.rollback()
    finally:
        db.close()

def mark_failed(email_id: int, reason: str):
    """Mark email as failed and increment retries"""
    try:
        db = SessionLocal()
        db.execute(
            text("""
                UPDATE OutEmail 
                SET retries = retries + 1, failed_reason = :reason 
                WHERE id = :id
            """),
            {'id': email_id, 'reason': reason}
        )
        db.commit()
    except Exception as e:
        logger.error(f"Error marking email {email_id} as failed: {e}")
        db.rollback()
    finally:
        db.close()

def log_error_sync(error_data):
    """Synchronous error logging"""
    try:
        db = SessionLocal()
        error_log = ErrorLogs(
            error=error_data.get('error', ''),
            service=error_data.get('service', 'EmailService'),
            source=error_data.get('source', 'Unknown'),
            occured_at=datetime.now()
        )
        db.add(error_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log error to database: {e}")
        db.rollback()
    finally:
        db.close()

# TASK DEFINITIONS
@app.task(bind=True, max_retries=3, default_retry_delay=30)
@trace_task
@profile_task
def scrape_unsent_emails(self):
    """Process unsent emails with observability"""
    task_id = self.request.id
    logger.set_task_id(task_id)
    
    tracer = get_tracer()
    
    logger.info("Starting unsent emails scrape", extra={
        'task_id': task_id,
        'operation': 'scrape_emails'
    })
    
    try:
        with tracer.start_as_current_span("get_unsent_emails") as span:
            emails = get_unsent_messages()
            span.set_attribute("emails.count", len(emails))
        
        logger.info(f"Found {len(emails)} unsent emails", extra={
            'task_id': task_id,
            'emails_count': len(emails)
        })
        
        for email in emails:
            try:
                with tracer.start_as_current_span("process_email") as span:
                    span.set_attribute("email.id", email['id'])
                    span.set_attribute("email.recipient", email['email'])
                    span.set_attribute("email.has_file", email['has_file'])
                    
                    logger.info(f"Processing email {email['id']}", extra={
                        'task_id': task_id,
                        'email_id': email['id'],
                        'recipient': email['email']
                    })
                    
                    if email['has_file'] == 1:
                        result = send_email_with_file.apply_async(
                            args=[email]
                        )
                        message, status = result.get(timeout=300)
                    else:
                        result = send_email.apply_async(
                            args=[email]
                        )
                        message, status = result.get(timeout=300)
                    
                    if status:
                        mark_sent(email['id'])
                        logger.info(f"Successfully sent email {email['id']}", extra={
                            'task_id': task_id,
                            'email_id': email['id'],
                            'status': 'sent'
                        })
                    else:
                        mark_failed(email['id'], message)
                        logger.warning(f"Failed to send email {email['id']}", extra={
                            'task_id': task_id,
                            'email_id': email['id'],
                            'status': 'failed',
                            'reason': message
                        })
                        
            except Exception as e:
                logger.error(f"Failed to process email {email['id']}", extra={
                    'task_id': task_id,
                    'email_id': email['id']
                }, exc_info=True)
                mark_failed(email['id'], str(e))
                continue
                
        logger.info("Completed unsent emails scrape", extra={
            'task_id': task_id,
            'operation': 'scrape_emails',
            'status': 'completed'
        })
                
    except Exception as exc:
        logger.error("Scrape unsent emails task failed", extra={
            'task_id': task_id,
            'operation': 'scrape_emails',
            'status': 'failed'
        }, exc_info=True)
        
        error_data = {
            'error': str(exc),
            'service': 'EmailService',
            'source': 'EmailService,ScrapeUnsentEmails',
            'occured_at': datetime.now().isoformat()
        }
        log_error_sync(error_data)
        raise self.retry(exc=exc)

@app.task(bind=True, max_retries=3, default_retry_delay=60)
@trace_task
@profile_task
def send_email(self, email_data):
    """Send email without attachment"""
    task_id = self.request.id
    logger.set_task_id(task_id)
    
    logger.info("Sending email", extra={
        'task_id': task_id,
        'email_id': email_data.get('id'),
        'recipient': email_data.get('email'),
        'operation': 'send_email'
    })
    
    try:
        # Your email sending logic here
        message = MIMEMultipart()
        message['From'] = 'Data G <datag@datag.co.ke>'
        message['To'] = email_data['email']
        message['Subject'] = email_data['subject']
        
        # Add HTML body with logo
        html_body = f"""
        <html>
            <body>
                {email_data['msg']}
                <br>
                <img src="cid:logo" width="120" height="100">
            </body>
        </html>
        """
        
        message.attach(MIMEText(html_body, 'html'))
        
        # Add logo as inline attachment
        logo_path = os.path.join(os.getcwd(), 'Images', 'logo.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_data = f.read()
            
            logo_attachment = MIMEBase('image', 'png')
            logo_attachment.set_payload(logo_data)
            encoders.encode_base64(logo_attachment)
            logo_attachment.add_header('Content-ID', '<logo>')
            logo_attachment.add_header('Content-Disposition', 'inline', filename='logo.png')
            message.attach(logo_attachment)
        
        # Send email
        with smtplib.SMTP_SSL('mail.datag.co.ke', 465) as server:
            server.login('datag@datag.co.ke', 'pswd')
            server.send_message(message)
        
        logger.info("Email sent successfully", extra={
            'task_id': task_id,
            'email_id': email_data.get('id'),
            'status': 'success'
        })
        
        return "Success", True
        
    except Exception as exc:
        logger.error("Email sending failed", extra={
            'task_id': task_id,
            'email_id': email_data.get('id'),
            'status': 'failed'
        }, exc_info=True)
        
        error_data = {
            'error': str(exc),
            'service': 'EmailService',
            'source': 'EmailService,SendEmail',
            'occured_at': datetime.now().isoformat()
        }
        log_error_sync(error_data)
        
        try:
            raise self.retry(exc=exc, countdown=60)
        except MaxRetriesExceededError:
            return str(exc), False

@app.task(bind=True, max_retries=3, default_retry_delay=60)
@trace_task
@profile_task
def send_email_with_file(self, email_data):
    """Send email with attachment"""
    task_id = self.request.id
    logger.set_task_id(task_id)
    
    logger.info("Sending email with attachment", extra={
        'task_id': task_id,
        'email_id': email_data.get('id'),
        'recipient': email_data.get('email'),
        'operation': 'send_email_with_file'
    })
    
    try:
        message = MIMEMultipart()
        message['From'] = 'Data G <datag@datag.co.ke>'
        message['To'] = email_data['email']
        message['Subject'] = email_data['subject']
        
        # Add HTML body
        message.attach(MIMEText(email_data['msg'], 'html'))
        
        # Add file attachment
        if email_data.get('file_to_be_sent'):
            file_data = base64.b64decode(email_data['file_to_be_sent'])
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(file_data)
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename={email_data.get("document_name", "attachment")}'
            )
            message.attach(attachment)
        
        # Add logo as inline attachment
        logo_path = os.path.join(os.getcwd(), 'Images', 'logo.png')
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_data = f.read()
            
            logo_attachment = MIMEBase('image', 'png')
            logo_attachment.set_payload(logo_data)
            encoders.encode_base64(logo_attachment)
            logo_attachment.add_header('Content-ID', '<logo>')
            logo_attachment.add_header('Content-Disposition', 'inline', filename='logo.png')
            message.attach(logo_attachment)
        
        # Send email
        with smtplib.SMTP_SSL('mail.datag.co.ke', 465) as server:
            server.login('datag@datag.co.ke', 'pswd')
            server.send_message(message)
        
        logger.info("Email with attachment sent successfully", extra={
            'task_id': task_id,
            'email_id': email_data.get('id'),
            'status': 'success'
        })
        
        return "Success", True
        
    except Exception as exc:
        logger.error("Email with attachment failed", extra={
            'task_id': task_id,
            'email_id': email_data.get('id'),
            'status': 'failed'
        }, exc_info=True)
        
        error_data = {
            'error': str(exc),
            'service': 'EmailService',
            'source': 'EmailService,SendEmailWithFile',
            'occured_at': datetime.now().isoformat()
        }
        log_error_sync(error_data)
        
        try:
            raise self.retry(exc=exc, countdown=60)
        except MaxRetriesExceededError:
            return str(exc), False

@app.task
@trace_task
def log_error(error_data):
    """Task for logging errors"""
    log_error_sync(error_data)

# Health check task
@app.task
def health_check():
    """Simple health check task"""
    logger.info("Health check - Celery is running")
    return "OK"