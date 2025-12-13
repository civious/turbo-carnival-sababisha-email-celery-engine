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
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
# Database functions
def get_unsent_messages():
    """Get unsent emails from database"""
    try:
        db = SessionLocal()
        query = text("""
             SELECT messageid, emaildisplayname,emailclientportnumber,encrypted,recipientemail,
            subject, body, contactemailpassword, contactemail,retries,subjecttitle
            FROM pos_shoes.dbo.unsentemailscraper

        """)

        result = db.execute(query)
        emails = []
        encryption_key = os.getenv('ENCRYPTION_KEY', '')

        for row in result:
            contact_password = row.contactemailpassword
            recipient_email = row.recipientemail

            # Password is ALWAYS encrypted - always decrypt it
            if contact_password and encryption_key:
                try:
                    contact_password = decrypt_data(contact_password, encryption_key)
                    logger.info(f"Decrypted password for email {row.messageid}")
                except Exception as decrypt_error:
                    logger.error(f"Failed to decrypt password for email {row.messageid}: {decrypt_error}")
                    # Keep encrypted password if decryption fails

            # Recipient email is only encrypted when encrypted flag = 1
            if row.encrypted == 1 and recipient_email and encryption_key:
                try:
                    recipient_email = decrypt_data(recipient_email, encryption_key)
                    logger.info(f"Decrypted recipient email for email {row.messageid}")
                except Exception as decrypt_error:
                    logger.error(f"Failed to decrypt recipient email for email {row.messageid}: {decrypt_error}")
                    # Keep encrypted recipient email if decryption fails

            emails.append({
                'id': row.messageid,
                'recipient': recipient_email,
                'subject': row.subject,
                'body': row.body,
                'emaildisplayname': row.emaildisplayname,
                'emailclientportnumber': row.emailclientportnumber,
                'retries': row.retries,
                'encrypted': row.encrypted,
                'contactemailpassword': contact_password,
                'contactemail': row.contactemail,
                'subjecttitle': row.subjecttitle
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
            text("UPDATE emailmessages SET statusflag = 1, status = 'SENT' WHERE messageid = :id"),
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
                SET retries = retries + 1,status='FAILED',  failedreason = :reason 
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
@trace_task
@profile_task
@app.task(bind=True, max_retries=3, default_retry_delay=30)
def scrape_unsent_emails(self):
    """Process unsent emails with observability"""
    task_id = self.request.id
    logger.set_task_ref(task_id)
    
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
                    span.set_attribute("email.recipient", email['recipient'])
                    
                    logger.info(f"Processing email {email['id']}", extra={
                        'task_id': task_id,
                        'email_id': email['id'],
                        'recipient': email['recipient']
                    })
                    
                    
                    result = send_email(task_id,
                            email)
                    message, status = result
                    
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

@trace_task
@profile_task
def send_email(task_id, email_data):
    """Send email without attachment"""
    logger.set_task_ref(task_id)
    
    logger.info("Sending email", extra={
        'task_id': task_id,
        'email_id': email_data.get('id'),
        'recipient': email_data.get('recepient'),
        'operation': 'send_email'
    })
    
    try:
        # Your email sending logic here
        message = MIMEMultipart()
        message['From'] = f'{email_data["emaildisplayname"]} <{email_data["contactemail"]}>'
        message['To'] = email_data['recipient']
        message['Subject'] = email_data['subject']
        
        # Add HTML body with logo and footer
        html_body = f"""
        <html>
            <body>
                {email_data['body']}
                <br><br>
                <hr style="border: none; border-top: 2px solid #e0e0e0; margin: 20px 0;">
                <table style="font-family: Arial, sans-serif; color: #333;">
                    <tr>
                        <td style="vertical-align: middle; padding-right: 20px;">
                            <img src="cid:logo" width="120" height="100" alt="Company Logo">
                        </td>
                        <td style="vertical-align: middle;">
                            <p style="margin: 5px 0; font-size: 14px;"><strong>For support, contact:</strong></p>
                            <p style="margin: 5px 0; font-size: 14px;">Civious Rumaita</p>
                            <p style="margin: 5px 0; font-size: 14px;">Phone: <a href="tel:+254715088150" style="color: #0066cc; text-decoration: none;">0715088150</a></p>
                        </td>
                    </tr>
                </table>
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
        
        # Extract SMTP server from contactemail domain
        smtp_server = email_data['contactemail'].split('@')[1] if '@' in email_data['contactemail'] else 'mail.sababisha.com'
        # Prepend 'mail.' if not already present
        if not smtp_server.startswith('mail.'):
            smtp_server = f'mail.{smtp_server}'

        smtp_port = int(email_data.get('emailclientportnumber', 465))

        logger.info(f"Attempting SMTP connection to {smtp_server}:{smtp_port} with user {email_data['contactemail']}", extra={
            'task_id': task_id,
            'smtp_server': smtp_server,
            'smtp_port': smtp_port,
            'email_user': email_data['contactemail']
        })

        # Send email
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(email_data['contactemail'], email_data['contactemailpassword'])
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
        
       
@trace_task
@profile_task
def send_email_with_file(task_id, email_data):
    """Send email with attachment"""
    logger.set_task_ref(task_id)
    
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
            server.login('datag@datag.co.ke', os.getenv('SMTP_PASSWORD'))
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

@trace_task
@profile_task
@app.task
def log_error(error_data):
    """Task for logging errors"""
    log_error_sync(error_data)
    

#decrypt data
def decrypt_data(encrypted_string: str, key: str) -> str:
    """
    Decrypt an AES-encrypted string using the provided key.
    
    Args:
        encrypted_string: Base64-encoded string with IV (first 24 chars) + encrypted data
        key: Encryption key as UTF-8 string
        
    Returns:
        Decrypted plaintext string
        
    Raises:
        ValueError: If encrypted_string or key is None or empty
    """
    # Validate the input string and key
    if not encrypted_string:
        raise ValueError("The encrypted string cannot be null or empty.")
    if not key:
        raise ValueError("The encryption key cannot be null or empty.")
    
    # Split the encrypted string into the IV and encrypted data
    iv_string = encrypted_string[:24]
    encrypted_data_string = encrypted_string[24:]
    
    # Convert the IV and encrypted data from Base64 to binary
    iv = base64.b64decode(iv_string)
    encrypted_data = base64.b64decode(encrypted_data_string)
    
    # Convert key to bytes
    key_bytes = key.encode('utf-8')
    
    # Create AES cipher in CBC mode
    cipher = Cipher(
        algorithms.AES(key_bytes),
        modes.CBC(iv),
        backend=default_backend()
    )
    
    # Decrypt the data
    decryptor = cipher.decryptor()
    decrypted_padded = decryptor.update(encrypted_data) + decryptor.finalize()
    
    # Remove PKCS7 padding
    padding_length = decrypted_padded[-1]
    decrypted_data = decrypted_padded[:-padding_length]
    
    # Convert bytes to string
    return decrypted_data.decode('utf-8')

# Health check task
@app.task
def health_check():
    """Simple health check task"""
    logger.info("Health check - Celery is running")
    return "OK"


if __name__ == "__main__":
    scrape_unsent_emails()