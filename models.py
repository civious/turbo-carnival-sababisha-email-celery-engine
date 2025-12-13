from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, SmallInteger
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class OutEmail(Base):
    __tablename__ = "OutEmail"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), nullable=False)
    subject = Column(String(500))
    msg = Column(Text)
    is_sent = Column(SmallInteger, default=0)  # Using SmallInteger for BIT equivalent
    retries = Column(Integer, default=0)
    failed_reason = Column(Text)
    has_file = Column(SmallInteger, default=0)
    file_to_be_sent = Column(Text)  # Storing base64 string
    document_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ErrorLogs(Base):
    __tablename__ = "ErrorLogs"
    
    id = Column(Integer, primary_key=True, index=True)
    error = Column(Text)
    service = Column(String(100))
    source = Column(String(200))
    occured_at = Column(DateTime, default=datetime.utcnow)