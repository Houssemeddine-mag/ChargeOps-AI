from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime

DATABASE_URL = "sqlite:///./wpt_data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TelemetryDB(Base):
    __tablename__ = "telemetry"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String)
    station_id = Column(String)
    temp_coil = Column(Float)
    temp_inverter = Column(Float)
    efficiency = Column(Float)
    coupling_k = Column(Float)
    frequency = Column(Float)
    v1 = Column(Float)
    i1 = Column(Float)
    v2 = Column(Float)
    i2 = Column(Float)
    q_factor = Column(Float)

class EventDB(Base):
    __tablename__ = "events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    station_id = Column(String)
    status_level = Column(String)
    probable_fault = Column(String)
    recommended_action = Column(String)
    estimated_rul_seconds = Column(Float, nullable=True)

Base.metadata.create_all(bind=engine)
