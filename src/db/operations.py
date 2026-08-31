"""Database operations for sessions and results."""

import json
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from sqlalchemy.orm import Session

from src.json_util import json_safe

from .models import (
    AnalysisSession,
    DailyComparison,
    EvaluationResult,
    SessionStatus,
    SkewSnapshot,
)


def create_session(user_id: str, db: Session) -> str:
    """Create a new analysis session and return its ID."""
    session_id = str(uuid4())
    session = AnalysisSession(
        session_id=session_id,
        user_id=user_id,
        status=SessionStatus.PENDING.value,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session_id


def get_session(session_id: str, db: Session) -> Optional[AnalysisSession]:
    """Get a session by ID."""
    return db.query(AnalysisSession).filter(AnalysisSession.session_id == session_id).first()


def update_session_status(session_id: str, status: str, db: Session) -> None:
    """Update session status."""
    session = get_session(session_id, db)
    if session:
        session.status = status
        session.updated_at = datetime.utcnow()
        db.commit()


def store_baseline_result(session_id: str, result: dict, db: Session) -> None:
    """Store baseline agent result."""
    session = get_session(session_id, db)
    if session:
        session.baseline_result = json.dumps(json_safe(result))
        session.updated_at = datetime.utcnow()
        db.commit()


def store_agent_result(session_id: str, result: dict, db: Session) -> None:
    """Store tool-based agent result."""
    session = get_session(session_id, db)
    if session:
        session.agent_result = json.dumps(json_safe(result))
        session.updated_at = datetime.utcnow()
        db.commit()


def store_eval_score(session_id: str, score: float, db: Session) -> None:
    """Store evaluation score."""
    session = get_session(session_id, db)
    if session:
        session.eval_score = score
        session.updated_at = datetime.utcnow()
        db.commit()


def store_error(session_id: str, error_message: str, db: Session) -> None:
    """Store error message and mark session as failed."""
    session = get_session(session_id, db)
    if session:
        session.error_message = error_message
        session.status = SessionStatus.FAILED.value
        session.updated_at = datetime.utcnow()
        db.commit()


def add_skew_snapshot(
    session_id: str,
    strike: float,
    skew_value: float,
    delta: Optional[float] = None,
    iv: Optional[float] = None,
    confidence: Optional[float] = None,
    date: Optional[datetime] = None,
    db: Session = None,
) -> None:
    """Add a skew snapshot to the database."""
    if not db:
        from .models import SessionLocal

        db = SessionLocal()

    snapshot = SkewSnapshot(
        session_id=session_id,
        strike=strike,
        skew_value=skew_value,
        delta=delta,
        iv=iv,
        confidence=confidence,
        date=date or datetime.utcnow(),
    )
    db.add(snapshot)
    db.commit()


def get_skew_snapshots(session_id: str, db: Session) -> list:
    """Get all skew snapshots for a session."""
    return db.query(SkewSnapshot).filter(SkewSnapshot.session_id == session_id).all()


def add_evaluation_result(
    session_id: str,
    case_id: str,
    difficulty: str,
    expected_skew: float,
    actual_skew: float,
    passed: bool,
    error_margin: Optional[float] = None,
    db: Session = None,
) -> None:
    """Add evaluation result."""
    if not db:
        from .models import SessionLocal

        db = SessionLocal()

    result = EvaluationResult(
        session_id=session_id,
        case_id=case_id,
        difficulty=difficulty,
        expected_skew=expected_skew,
        actual_skew=actual_skew,
        passed=1 if passed else 0,
        error_margin=error_margin,
    )
    db.add(result)
    db.commit()


def get_evaluation_results(session_id: str, db: Session) -> list:
    """Get all evaluation results for a session."""
    return db.query(EvaluationResult).filter(EvaluationResult.session_id == session_id).all()


def get_recent_sessions(user_id: str, days: int = 7, db: Session = None) -> list:
    """Get recent sessions for a user."""
    if not db:
        from .models import SessionLocal

        db = SessionLocal()

    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(AnalysisSession)
        .filter(AnalysisSession.user_id == user_id, AnalysisSession.created_at >= cutoff)
        .order_by(AnalysisSession.created_at.desc())
        .all()
    )


def add_daily_comparison(
    date: datetime,
    baseline_skew: float,
    agent_skew: float,
    baseline_confidence: Optional[float] = None,
    agent_confidence: Optional[float] = None,
    db: Session = None,
) -> None:
    """Add a daily comparison record."""
    if not db:
        from .models import SessionLocal

        db = SessionLocal()

    improvement = (agent_skew - baseline_skew) / baseline_skew * 100 if baseline_skew != 0 else 0

    comparison = DailyComparison(
        date=date,
        baseline_skew=baseline_skew,
        agent_skew=agent_skew,
        baseline_confidence=baseline_confidence,
        agent_confidence=agent_confidence,
        improvement=improvement,
    )
    db.add(comparison)
    db.commit()


def get_daily_comparisons(days: int = 30, db: Session = None) -> list:
    """Get daily comparisons over the last N days."""
    if not db:
        from .models import SessionLocal

        db = SessionLocal()

    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(DailyComparison)
        .filter(DailyComparison.date >= cutoff)
        .order_by(DailyComparison.date.desc())
        .all()
    )
