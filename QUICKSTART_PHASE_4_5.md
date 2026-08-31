# Quick Start: Phase 4 & 5 - Full System

## 60-Second Setup

### Terminal 1: Setup & Database
```bash
cd "d:/Crossseas Capital/CCSPL_CANDIDATE_TEST/CCSPL_CANDIDATE_TEST"
make setup
make db-init
```

### Terminal 2: API Server
```bash
cd "d:/Crossseas Capital/CCSPL_CANDIDATE_TEST/CCSPL_CANDIDATE_TEST"
make api
# Server starts at http://localhost:8000
```

### Terminal 3: Frontend Dev
```bash
cd "d:/Crossseas Capital/CCSPL_CANDIDATE_TEST/CCSPL_CANDIDATE_TEST/frontend"
npm run dev
# Dashboard at http://localhost:5173
```

### Terminal 4: Run Pipeline
```bash
cd "d:/Crossseas Capital/CCSPL_CANDIDATE_TEST/CCSPL_CANDIDATE_TEST"
make pipeline
```

---

## What Happens

### API Server Output
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Database initialized
INFO:     Application startup complete
```

### Pipeline Output
```
============================================================
Nifty Options Skew Analysis - Production Pipeline
Phases: 1, 2, 3, 4, 5
============================================================
=== Phase 1: Setup ===
✓ Database initialized
✓ CSV file found: OPTIONS_DATA/nifty_options.csv

=== Phase 2: Baseline Analysis ===
✓ Baseline analysis completed

=== Phase 3: Agent Analysis ===
✓ Agent analysis completed

=== Phase 4: Evaluation ===
✓ Evaluation completed: 9/11 passed (81.8%)

=== Phase 5: Report Generation ===
✓ Report generated: reports/report_<session-id>.md

============================================================
Pipeline Execution Complete
Session ID: <uuid>
Baseline: ✓
Agent: ✓
Evaluation Score: 81.8%
Report: reports/report_<uuid>.md
============================================================
```

### Dashboard
1. Open http://localhost:5173
2. Sign in:
   - Email: `analyst@local.dev`
   - Password: `password123`
3. Dashboard displays:
   - Session skew curve
   - Metrics cards
   - Baseline vs Agent comparison
   - Agent trajectory steps
   - Evaluation results

---

## Verify Components

### Database
```bash
# Check database was created
ls vol_skew.db

# Query sessions (from Python)
python -c "
from src.db.models import SessionLocal
from src.db.operations import get_recent_sessions
db = SessionLocal()
sessions = get_recent_sessions('demo-user', db=db)
print(f'Sessions: {len(sessions)}')
for s in sessions:
    print(f'  - {s.session_id}: {s.status} (score: {s.eval_score})')
db.close()
"
```

### API Endpoints
```bash
# Health check
curl http://localhost:8000/health
# {"status":"healthy"}

# Create session
curl -X POST http://localhost:8000/api/sessions?user_id=demo-user
# {"session_id":"...","user_id":"demo-user","status":"pending",...}

# List sessions
curl http://localhost:8000/api/sessions/user/demo-user
# [{"session_id":"...","status":"completed","eval_score":81.8,...}]

# Get comparisons
curl http://localhost:8000/api/data/comparisons?days=7
# [{"date":"...","baseline_skew":0.12,"agent_skew":0.125,"improvement":4.17,...}]
```

### Frontend
- Navigate to http://localhost:5173
- Verify all sections load
- Dashboard data comes from database via API

---

## File Structure

```
├── src/
│   ├── db/
│   │   ├── models.py          ← SQLAlchemy models
│   │   ├── operations.py      ← CRUD functions
│   │   └── __init__.py
│   ├── api/
│   │   ├── server.py          ← FastAPI server
│   │   └── __init__.py
│   └── pipeline.py            ← 5-phase orchestrator
├── frontend/
│   ├── src/
│   │   ├── hooks/
│   │   │   └── useApi.ts      ← API client hooks
│   │   ├── types/
│   │   │   └── app.ts         ← Type definitions
│   │   └── ...
│   └── package.json
├── PHASE_4_5.md               ← Full documentation
├── PHASE_4_5_SUMMARY.md       ← Completion summary
├── Makefile                   ← All commands
├── requirements.txt           ← Dependencies
└── vol_skew.db               ← SQLite database (created on first run)
```

---

## Commands Reference

### Setup & Database
```bash
make setup          # Install dependencies
make db-init        # Initialize SQLite database
make clean          # Remove database files
```

### Server
```bash
make api            # Start FastAPI server (port 8000)
```

### Pipeline
```bash
make pipeline           # Run full pipeline (phases 1-5)
make pipeline-demo      # Run pipeline without database
python src/pipeline.py --phases 2,3    # Run only phases 2-3
python src/pipeline.py --csv-path <path>  # Custom data file
```

### Frontend
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Start dev server (port 5173)
npm run build        # Production build
npm run preview      # Preview production build
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'src'"
```bash
# Ensure you're in the root directory
cd "d:/Crossseas Capital/CCSPL_CANDIDATE_TEST/CCSPL_CANDIDATE_TEST"
# Then run commands
```

### "ANTHROPIC_API_KEY not set"
```bash
# Set the environment variable
$env:ANTHROPIC_API_KEY = "sk-..."
# Or in .env file
```

### "Port 8000 already in use"
```bash
# Use a different port
python -m uvicorn src.api.server:app --port 8001
# Update frontend .env: VITE_API_URL=http://localhost:8001
```

### "Frontend can't reach API"
```bash
# Ensure API server is running on port 8000
# Check .env.local has correct VITE_API_URL
# Browser console will show fetch errors if API is unreachable
```

### "Database locked"
```bash
# SQLite locks when multiple writers access simultaneously
# Ensure only one pipeline is running
# Close the database browser/viewer
```

---

## What Was Built

### Phase 4: Database/State Persistence
- ✅ SQLite database with 4 tables
- ✅ SQLAlchemy ORM layer
- ✅ CRUD operations (create, read, update, delete)
- ✅ REST API server (6 endpoints)
- ✅ Frontend React hooks for API calls
- ✅ Graceful fallback to mock data

### Phase 5: End-to-End Pipeline
- ✅ 5-phase orchestrator (setup → baseline → agent → eval → report)
- ✅ Database persistence
- ✅ Comprehensive logging
- ✅ Error handling
- ✅ Selective phase execution
- ✅ Demo mode (no database)
- ✅ Markdown report generation

### Integration
- ✅ Frontend ↔ API ↔ Database
- ✅ Pipeline stores results in database
- ✅ Dashboard retrieves and displays results
- ✅ Real/mock data fallback

---

## Next Steps

1. **Run end-to-end**: Follow 60-second setup above
2. **Verify database**: Check `vol_skew.db` was created
3. **Test API**: Use curl commands from "Verify Components"
4. **View dashboard**: Open http://localhost:5173
5. **Read reports**: Check `reports/` directory for markdown output
6. **Explore code**: See PHASE_4_5.md for architecture details

---

## Production Deployment

When ready to deploy:

1. **Database**: Migrate from SQLite to PostgreSQL (Supabase)
   - Update `DATABASE_URL` in `.env`
   - No code changes needed (SQLAlchemy is agnostic)

2. **API**: Deploy with production ASGI server
   - Use Gunicorn + Uvicorn
   - Run behind Nginx reverse proxy
   - Enable HTTPS

3. **Frontend**: Build and deploy static assets
   ```bash
   cd frontend && npm run build
   # Deploy frontend/dist/ to CDN or static hosting
   ```

4. **Environment**: Set production environment variables
   - `ANTHROPIC_API_KEY`
   - `VITE_API_URL` (production backend URL)
   - `VITE_SUPABASE_*` (if using Supabase auth)

---

## Support

For detailed information, see:
- **PHASE_4_5.md** - Full technical documentation
- **PHASE_4_5_SUMMARY.md** - Features and capabilities
- **Makefile** - All available commands
- **src/pipeline.py** - Pipeline implementation
- **src/api/server.py** - API server implementation
- **frontend/src/hooks/useApi.ts** - Frontend API client
