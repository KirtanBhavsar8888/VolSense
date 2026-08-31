# Changelog

All notable changes to this project are documented here.

## Unreleased

### Added
- Documented the full skew-analysis pipeline in the project README.
- Added reproducible setup commands via Makefile and pinned dependency file.
- Added a reproduction guide in `REPRODUCE.md`.
- Added a synthetic evaluation harness in `eval/run_eval.py` and `eval/cases.json`.
- Added memory-backed daily skew comparison support in `src/agent/memory.py`.
- Added markdown and plot report generation in `src/agent/report_agent.py` and `src/report/render.py`.

### Fixed
- Corrected the DTE calculation alignment between validation and parity logic.
- Fixed None-value formatting in report generation.
- Added headless matplotlib backend config for CI-safe rendering.
- Improved agent reroute reasoning to reflect actual flagged issues.
- Updated eval cases to use valid interpolation inputs for 25-delta skew extraction.

## Completed project components

- Calc layer extracted and validated
- Regression tests added for notebook-based pricing checks
- Baseline direct-prompt agent implemented
- Tool-aware analysis agent implemented
- Verification gate added for sanity checks
- Memory layer added for daily skew snapshots
- Report generation added for markdown and plots
- Evaluation harness completed with synthetic scoring cases
- Reproducible setup and commands added

## Notes

This changelog reflects the implementation state as built in the workspace and does not include unverified benchmark claims or invented metrics. Historical results, execution counts, or pass rates should be taken only from actual project runs and saved artifacts, not from the documentation here.
