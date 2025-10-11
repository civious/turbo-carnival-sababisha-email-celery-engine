import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import urllib.parse

class MSSQLConfig:
    def __init__(self):
        self.driver = os.getenv('MSSQL_DRIVER', 'ODBC Driver 17 for SQL Server')
        self.server = os.getenv('MSSQL_SERVER', 'localhost')
        self.database = os.getenv('MSSQL_DATABASE', 'your_database')
        self.username = os.getenv('MSSQL_USERNAME', 'your_username')
        self.password = os.getenv('MSSQL_PASSWORD', 'your_password')
        self.port = os.getenv('MSSQL_PORT', '1433')
        
    @property
    def connection_string(self):
        # URL encode the password to handle special characters
        encoded_password = urllib.parse.quote_plus(self.password)
        
        return (
            f"mssql+pymssql://{self.username}:{encoded_password}@"
            f"{self.server}:{self.port}/{self.database}"
            # f"driver={self.driver}&TrustServerCertificate=yes"
        )

# Create engine with connection pooling
engine = create_engine(
    MSSQLConfig().connection_string,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=False  # Set to True for debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()