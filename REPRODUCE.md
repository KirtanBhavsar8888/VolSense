# Reproduction guide

This repository expects a Python environment with the pinned dependencies in requirements.txt.

## 1) Setup

```bash
make setup
```

This creates `.venv`, upgrades pip, and installs the pinned stack.

## 2) Baseline run

```bash
ANTHROPIC_API_KEY="<your-key>" make baseline
```

This runs the naive direct-prompt baseline against the first eval case converted to a temporary CSV.

## 3) Tool-using agent run

```bash
ANTHROPIC_API_KEY="<your-key>" make agent
```

This runs the analysis agent on the first eval case using the tool loop.

## 4) Full evaluation

```bash
make eval
```

This executes the scorer in `eval/run_eval.py` and writes results under `eval/results/`.

## Notes

- The project uses `ANTHROPIC_API_KEY` for the baseline and agent runs.
- The eval harness expects `eval/cases.json` and the source code in `src/`.
- If you are on Windows PowerShell, run the same commands after activating the venv or use the equivalent `python`/`pip` commands.
