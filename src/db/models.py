"""Database models for sessions, skew snapshots, and evaluation results."""

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

DATABASE_URL = "sqlite:///./vol_skew.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class SessionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisSession(Base):
    """Stores a single analysis run session."""

    __tablename__ = "analysis_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    user_id = Column(String, index=True)
    status = Column(String, default=SessionStatus.PENDING.value)
    model = Column(String, default="openai/gpt-oss-20b")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    baseline_result = Column(Text, nullable=True)
    agent_result = Column(Text, nullable=True)
    eval_score = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)


class SkewSnapshot(Base):
    """Stores a skew measurement at a point in time."""

    __tablename__ = "skew_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    date = Column(DateTime, index=True, default=datetime.utcnow)
    strike = Column(Float, index=True)
    skew_value = Column(Float)
    delta = Column(Float, nullable=True)
    iv = Column(Float, nullable=True)
    confidence = Column(Float, nullable=True)


class EvaluationResult(Base):
    """Stores evaluation case results."""

    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    case_id = Column(String, index=True)
    difficulty = Column(String)
    expected_skew = Column(Float)
    actual_skew = Column(Float)
    passed = Column(Integer)  # 0 or 1
    error_margin = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DailyComparison(Base):
    """Stores baseline vs agent comparison for a day."""

    __tablename__ = "daily_comparisons"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True, default=datetime.utcnow)
    baseline_skew = Column(Float)
    agent_skew = Column(Float)
    baseline_confidence = Column(Float, nullable=True)
    agent_confidence = Column(Float, nullable=True)
    improvement = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)


def init_db():
    """Initialize the database with all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
