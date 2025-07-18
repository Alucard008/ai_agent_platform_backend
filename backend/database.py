# backend/database.py
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL in .env")

engine = create_engine(DATABASE_URL, echo=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# *** single declarative base ***
Base = declarative_base()

def init_db():
    # import your models module *after* Base is defined
    from backend import models   # ← make sure this matches how you run uvicorn
    print("🗄️  Tables known to SQLAlchemy:", list(Base.metadata.tables.keys()))
    Base.metadata.create_all(bind=engine)
    print("✅ create_all complete")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
