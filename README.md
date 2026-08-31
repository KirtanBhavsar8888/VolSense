# Nifty Options Skew Research Agent

This project builds a deterministic research pipeline for Nifty option-chain skew analysis. It combines a calc layer, verification gate, baseline LLM response, tool-using analysis agent, memory layer, reporting, and evaluation harness.

## What is included

- Synthetic future parity calculations for option chains
- Black-Scholes IV / delta solving and validation
- 25-delta skew interpolation and skew validation
- pre-flight sanity checks for no-arbitrage and edge-case rejection
- baseline prompt-only agent for comparison against a tool-using agent
- daily skew memory persistence and day-over-day comparison
- markdown + plot report generation
- evaluation suite covering known-good synthetic scenarios
- reproducible local setup via Makefile and pinned requirements

## Project layout

- `src/calc/` — core pricing and skew calculations
  - `parity.py`
  - `iv.py`
  - `skew.py`
- `src/verification/` — sanity gate and bounds checks
  - `bounds_check.py`
- `src/agent/` — agent orchestration layers
  - `baseline.py`
  - `analysis_agent.py`
  - `memory.py`
  - `tools.py`
  - `report_agent.py`
- `src/report/` — plot rendering
  - `render.py`
- `eval/` — synthetic evaluation cases and runner
  - `cases.json`
  - `run_eval.py`
- `tests/` — regression checks for calculator behavior
- `OPTIONS_DATA/` — parquet option-chain data used for pattern validation and research work
- `Makefile`, `requirements.txt`, `REPRODUCE.md` — reproducibility targets

## Core workflow

1. Load the option chain.
2. Run sanity checks to reject invalid or near-expiry / illiquid chains.
3. Compute synthetic futures, IV/delta, and 25-delta skew.
4. Persist daily skew snapshots for comparison.
5. Generate a markdown report and summary plots.
6. Evaluate against reference scenarios.

## Baseline vs tool agent

Two analysis modes are implemented:

- `baseline_agent_response(...)` — direct prompt-only LLM call using the raw CSV context
- `run_analysis_agent(...)` — tool-using workflow that computes and validates chain metrics before summarizing results

This gives a clear contrast between a naive agent and a deterministic tool-assisted workflow.

## Setup

```bash
make setup
```

This creates a local virtual environment and installs the pinned dependencies from `requirements.txt`.

## Run the project

### Baseline model

```bash
ANTHROPIC_API_KEY="<your-key>" make baseline
```

### Tool-using agent

```bash
ANTHROPIC_API_KEY="<your-key>" make agent
```

### Full eval suite

```bash
make eval
```

See `REPRODUCE.md` for the full local reproduction flow.

## Notes

- The evaluation framework is built around synthetic cases stored in `eval/cases.json`.
- Reporting is implemented with matplotlib in headless `Agg` mode for CI-safe execution.
- The daily memory layer stores snapshots and compares recent skew summaries to the current session.
- The code is designed to work with option-chain data in a pandas DataFrame or CSV-driven inputs.

## Intended use

This project is intended for research and validation of skew behavior in Nifty options data, especially for:

- sanity-gating invalid chains
- quantifying 25-delta skew shifts
- day-over-day comparisons
- comparing direct-prompt and tool-using analysis quality

## Environment requirements

- Python 3.10+
- `ANTHROPIC_API_KEY` for the LLM-based baseline and analysis agent
- Local dependencies pinned in `requirements.txt`
