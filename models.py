from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class Woreda(Base):
    __tablename__ = 'woredas'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    kebeles = relationship("Kebele", back_populates="woreda", cascade="all, delete-orphan")

class Kebele(Base):
    __tablename__ = 'kebeles'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    woreda_id = Column(Integer, ForeignKey('woredas.id'))
    woreda = relationship("Woreda", back_populates="kebeles")

class Farmer(Base):
    __tablename__ = 'farmers'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String, nullable=False)
    woreda = Column(String)
    kebele = Column(String)
    phone = Column(String)
    audio_data = Column(Text)  # Base64 string of the audio
    registered_by = Column(String)

def create_tables():
    from database import engine
    Base.metadata.create_all(bind=engine)
