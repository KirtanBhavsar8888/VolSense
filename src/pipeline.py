"""End-to-end production pipeline for Nifty options skew analysis."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_io import DEFAULT_CSV_PATH, ensure_sample_csv
from src.db.models import SessionLocal, init_db
from src.db.operations import create_session, update_session_status
from src.workflow import run_full_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Nifty Options Skew Analysis Pipeline")
    parser.add_argument("--csv-path", default=str(DEFAULT_CSV_PATH), help="Path to options data CSV")
    parser.add_argument("--user-id", default="demo-user", help="User ID for the session")
    parser.add_argument(
        "--skip-database",
        action="store_true",
        help="Skip database operations",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Nifty Options Skew Analysis - Production Pipeline")
    logger.info("=" * 60)

    csv_path = ensure_sample_csv(args.csv_path)
    logger.info("Using chain file: %s", csv_path)

    init_db()
    db = None if args.skip_database else SessionLocal()
    session_id = "demo-session"

    try:
        if db is not None:
            session_id = create_session(args.user_id, db)
            logger.info("Created session: %s", session_id)
            update_session_status(session_id, "running", db)

        result = run_full_pipeline(
            session_id=session_id,
            csv_path=csv_path,
            db=db,
            skip_database=args.skip_database,
        )

        logger.info("=" * 60)
        logger.info("Pipeline Execution Complete")
        logger.info("Session ID: %s", result["session_id"])
        logger.info("Rows: %s", result["rows"])
        logger.info("LLM agents: %s", "on" if result["used_llm"] else "off (calc layer only)")
        logger.info("Close 25d skew: %s", result["close_skew"])
        logger.info("Evaluation score: %.1f%%", result["eval_score"] or 0.0)
        logger.info("Report: %s", result["report_path"] or "n/a")
        logger.info("=" * 60)
        return 0
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        return 1
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    sys.exit(main())
