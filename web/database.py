import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DB_CONNECTION_STRING")

if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("DB_CONNECTION_STRING environment variable not set")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    # Import all models here before calling Base.metadata.create_all
    # This ensures that SQLAlchemy knows about them
    from . import models # Assuming models.py is in the same directory
    Base.metadata.create_all(bind=engine)
