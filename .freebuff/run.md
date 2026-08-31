# Preview Run Doc — Freebuff Desktop

## How to Reproduce Uncommitted Artifacts

No uncommitted artifacts needed — all files are already in the worktree.

### Backend Setup (one-time)
```bash
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -c "from src.db.models import init_db; init_db(); print('Database initialized')"
```

### Frontend Setup (one-time)
```bash
cd frontend
npm install
```

## How to Run

### Terminal 1 — Backend API (port 8000)
```bash
set GROQ_API_KEY=your-groq-api-key
.venv/Scripts/python -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### Terminal 2 — Frontend Vite Dev Server (port 5173)
```bash
cd frontend
npm run dev
```

The frontend (`VITE_API_URL=http://localhost:8000`) talks to the backend automatically.

## Pages

- `/login` — Sign in with Google or Email/Password, Create Account
- `/dashboard` — Main dashboard with skew chart, metrics, comparison, trajectory, eval
- `/comparison` — List of comparison runs with expand/collapse (react-spring animation)
- `/tool-trace` — Full tool call timeline with syntax-highlighted JSON
- `/eval-results` — Pass-rate bars, difficulty filter pills, expandable case rows

## API Keys

- **Groq**: Use `GROQ_API_KEY` environment variable (free tier: `openai/gpt-oss-20b` model)
- **Supabase**: Configure in `frontend/.env` with `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`
