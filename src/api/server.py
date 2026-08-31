"""FastAPI server for the Nifty options skew analysis dashboard."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

# Load .env file from project root
from dotenv import load_dotenv

project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / ".env")

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.backtest.engine import run_backtest
from src.data_io import DEFAULT_CSV_PATH, load_chain
from src.db.models import SessionLocal, get_db, init_db
from src.db.operations import (
    create_session,
    get_daily_comparisons,
    get_evaluation_results,
    get_recent_sessions,
    get_session,
    get_skew_snapshots,
    store_error,
)
from src.workflow import run_full_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nifty Options Skew Analysis API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BacktestRequest(BaseModel):
    strategy: dict = Field(default={"type": "atm_straddle", "direction": "long", "quantity": 1})
    entry_time: str = Field(default="2026-08-28 10:30:00")
    exit_rule: dict = Field(default={"stop_loss_pct": 5.0, "take_profit_pct": 10.0, "max_hold_minutes": 375})
    csv_path: str = Field(default=str(DEFAULT_CSV_PATH))
    lot_size: Optional[int] = None
    num_lots: int = 1


class RunAnalysisRequest(BaseModel):
    session_id: Optional[str] = None
    csv_path: str = Field(default=str(DEFAULT_CSV_PATH))
    user_id: str = "demo-user"


@app.on_event("startup")
def startup():
    """Initialize database on startup."""
    init_db()
    logger.info("Database initialized")


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/sessions")
def create_analysis_session(user_id: str = "demo-user", db: Session = Depends(get_db)):
    """Create a new analysis session."""
    try:
        session_id = create_session(user_id, db)
        session = get_session(session_id, db)
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "status": session.status,
            "created_at": session.created_at.isoformat(),
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/user/{user_id}")
def list_user_sessions(user_id: str, days: int = 7, db: Session = Depends(get_db)):
    """List recent sessions for a user."""
    try:
        sessions = get_recent_sessions(user_id, days, db)
        return [
            {
                "session_id": s.session_id,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "eval_score": s.eval_score,
            }
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
def get_session_details(session_id: str, db: Session = Depends(get_db)):
    """Get details of a specific session."""
    session = get_session(session_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    skew_snapshots = get_skew_snapshots(session_id, db)
    eval_results = get_evaluation_results(session_id, db)

    baseline_result = None
    agent_result = None
    if session.baseline_result:
        try:
            baseline_result = json.loads(session.baseline_result)
        except json.JSONDecodeError:
            baseline_result = {"raw": session.baseline_result}
    if session.agent_result:
        try:
            agent_result = json.loads(session.agent_result)
        except json.JSONDecodeError:
            agent_result = {"raw": session.agent_result}

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "status": session.status,
        "model": session.model,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "baseline_result": baseline_result,
        "agent_result": agent_result,
        "eval_score": session.eval_score,
        "error_message": session.error_message,
        "skew_snapshots": [
            {
                "strike": s.strike,
                "skew_value": s.skew_value,
                "delta": s.delta,
                "iv": s.iv,
                "confidence": s.confidence,
                "date": s.date.isoformat() if s.date else None,
            }
            for s in skew_snapshots
        ],
        "evaluation_results": [
            {
                "case_id": r.case_id,
                "difficulty": r.difficulty,
                "expected_skew": r.expected_skew,
                "actual_skew": r.actual_skew,
                "passed": bool(r.passed),
                "error_margin": r.error_margin,
            }
            for r in eval_results
        ],
    }


@app.get("/api/data/comparisons")
def get_comparisons(days: int = 30, db: Session = Depends(get_db)):
    """Get daily baseline vs agent comparisons."""
    try:
        comparisons = get_daily_comparisons(days, db)
        return [
            {
                "date": c.date.isoformat(),
                "baseline_skew": c.baseline_skew,
                "agent_skew": c.agent_skew,
                "improvement": c.improvement,
                "baseline_confidence": c.baseline_confidence,
                "agent_confidence": c.agent_confidence,
            }
            for c in comparisons
        ]
    except Exception as e:
        logger.error(f"Error fetching comparisons: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def run_pipeline_job(session_id: str, csv_path: str) -> None:
    """Background task: open a fresh DB session and run the full pipeline."""
    db = SessionLocal()
    try:
        run_full_pipeline(session_id=session_id, csv_path=csv_path, db=db)
        logger.info(f"Session {session_id} completed successfully")
    except Exception as e:
        logger.error(f"Pipeline error for session {session_id}: {e}")
        try:
            store_error(session_id, str(e), db)
        except Exception:
            logger.exception("Failed to persist pipeline error")
    finally:
        db.close()


@app.post("/api/run")
def run_analysis(
    payload: RunAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Trigger a full analysis run."""
    try:
        session_id = payload.session_id or create_session(payload.user_id, db)
        background_tasks.add_task(run_pipeline_job, session_id, payload.csv_path)
        return {
            "session_id": session_id,
            "message": "Analysis pipeline started",
            "status": "running",
        }
    except Exception as e:
        logger.error(f"Error triggering analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{session_id}")
def get_status(session_id: str, db: Session = Depends(get_db)):
    """Get current status of a session."""
    session = get_session(session_id, db)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": session_id,
        "status": session.status,
        "eval_score": session.eval_score,
        "updated_at": session.updated_at.isoformat(),
        "error_message": session.error_message,
    }


@app.post("/api/backtest")
def run_backtest_endpoint(payload: BacktestRequest):
    """Run a strategy backtest."""
    try:
        chain_df = load_chain(payload.csv_path)
        result = run_backtest(
            chain_df=chain_df,
            strategy=payload.strategy,
            entry_time=payload.entry_time,
            exit_rule=payload.exit_rule,
            lot_size=payload.lot_size,
            num_lots=payload.num_lots,
        )
        return result
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
