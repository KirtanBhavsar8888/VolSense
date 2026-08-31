PYTHON ?= python
VENV_DIR := .venv

ifeq ($(OS),Windows_NT)
VENV_PY := $(VENV_DIR)\Scripts\python.exe
else
VENV_PY := $(VENV_DIR)/bin/python
endif

.PHONY: setup baseline agent eval api pipeline db-init clean

setup:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_PY) -m pip install --upgrade pip
	$(VENV_PY) -m pip install -r requirements.txt

baseline:
	ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} $(VENV_PY) -c "import json, pandas as pd, tempfile, os; case=json.load(open('eval/cases.json'))[0]; df=pd.DataFrame(case['chain_snippet']['rows']); df.to_csv('tmp_baseline_chain.csv', index=False); from src.agent.baseline import baseline_agent_response; print(baseline_agent_response('tmp_baseline_chain.csv'))"
	@rm -f tmp_baseline_chain.csv

agent:
	ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} $(VENV_PY) -c "import json, pandas as pd; from src.agent.analysis_agent import run_analysis_agent; case=json.load(open('eval/cases.json'))[0]; df=pd.DataFrame(case['chain_snippet']['rows']); df['timestamp']=pd.to_datetime(df['timestamp']); df['expiry']=pd.to_datetime(df['expiry']); print(run_analysis_agent(df, max_tool_rounds=2))"

eval:
	$(VENV_PY) -m eval.run_eval eval/results

db-init:
	$(VENV_PY) -c "from src.db.models import init_db; init_db(); print('✓ Database initialized')"

api:
	ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} $(VENV_PY) -m uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload

pipeline:
	ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} $(VENV_PY) -m src.pipeline --csv-path OPTIONS_DATA/nifty_options.csv

pipeline-demo:
	ANTHROPIC_API_KEY=$${ANTHROPIC_API_KEY} $(VENV_PY) -m src.pipeline --skip-database

clean:
	rm -f vol_skew.db
	rm -rf reports
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
