from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Using v2 to ensure fresh schema for 2025 survey
DATABASE_URL = "sqlite:///./amhara_survey_2025.db"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
