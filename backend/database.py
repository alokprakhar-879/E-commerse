import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

TARGET_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ecommerce_db"
)

# Connect with automatic fallback if PostgreSQL service is not yet running locally
engine = None
DATABASE_URL = TARGET_DATABASE_URL

if TARGET_DATABASE_URL.startswith("postgresql"):
    try:
        # Check if PostgreSQL is actively listening
        test_engine = create_engine(
            TARGET_DATABASE_URL,
            connect_args={"connect_timeout": 1},
            pool_pre_ping=True
        )
        with test_engine.connect() as conn:
            pass
        engine = test_engine
        print(f"[DBMS Engine] Connected successfully to PostgreSQL at {TARGET_DATABASE_URL}")
    except Exception:
        fallback_url = "sqlite:///ecommerce_dev.db"
        DATABASE_URL = fallback_url
        print(
            f"[DBMS Engine Notice] PostgreSQL service not detected on localhost:5432.\n"
            f"Using local SQLite fallback ({fallback_url}) so the application runs immediately.\n"
            f"To switch to PostgreSQL, start Postgres and ensure DATABASE_URL is set in .env."
        )
        engine = create_engine(
            fallback_url,
            connect_args={"check_same_thread": False}
        )
else:
    connect_args = {"check_same_thread": False} if TARGET_DATABASE_URL.startswith("sqlite") else {}
    engine = create_engine(TARGET_DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Database session dependency. Yields an isolated session per request
    and ensures clean closure upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
