import os
import logging
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from .model import YouTubeNote

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_database_if_not_exists():
    db_path = Path(os.environ.get("YOUTUBE_NOTE_DB", os.path.join(os.path.dirname(__file__), "..", "..", "..", "youtube_notes.db")))
    db_path = db_path.resolve()
    db_dir = db_path.parent

    if not db_dir.exists():
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created database directory: {db_dir}")

    if not db_path.exists():
        logger.info(f"Database file not found. It will be created: {db_path}")
    else:
        logger.info(f"Database file found: {db_path}")

def initialize_database():
    try:
        create_database_if_not_exists()

        db_path = Path(os.environ.get("YOUTUBE_NOTE_DB", os.path.join(os.path.dirname(__file__), "..", "..", "..", "youtube_notes.db"))).resolve()
        engine = create_engine(f'sqlite:///{db_path}', echo=True)

        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created successfully")

        try:
            with engine.connect() as conn:
                result = conn.exec_driver_sql('PRAGMA table_info(youtube_note)')
                columns = [row[1] for row in result.fetchall()]
                if 'title' not in columns:
                    logger.info("Adding missing 'title' column to youtube_note table")
                    conn.exec_driver_sql('ALTER TABLE youtube_note ADD COLUMN title VARCHAR')
                    logger.info("Added 'title' column successfully")
        except Exception as mig_err:
            logger.warning(f"Database migration check failed or not needed: {mig_err}")

        return engine
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

engine = initialize_database()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


