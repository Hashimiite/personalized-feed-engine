import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

# DATABASE_URL wins when set (Docker Compose, CI); otherwise build it from the DB_* values in .env
DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql://{os.getenv('DB_USER', 'feed')}:{os.getenv('DB_PASSWORD', 'feed')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'feed')}"
)

engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=10)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
