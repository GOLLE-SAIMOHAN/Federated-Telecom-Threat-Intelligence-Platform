# Implementation Status

## Current phase

**Threat Intelligence layer**

## Completed

- Established the planned repository structure.
- Added authoritative-project guidance in `AGENTS.md`.
- Added Python dependency manifest and project configuration.
- Added backend and frontend dependency manifests.
- Generated backend and frontend lockfiles after dependency resolution.
- Added environment-variable template and ignore rules.
- Added baseline documentation and experiment-log templates.

## Phase 2 implemented

- Added reusable dataset loading for CSV, Parquet, Excel, and directories of
  matching tabular files.
- Added dataset structure validation and inspection reporting.
- Added missing-value and duplicate-row analysis.
- Added explicit label-column configuration; no label or feature names are
  assumed.
- Added reusable numeric imputation/scaling and categorical imputation/one-hot
  preprocessing.
- Added reproducible label encoding and stratified train/test splitting.
- Added four logical operator partitions.
- Added reproducible IID partitioning and configurable Dirichlet non-IID
  partitioning.
- Added JSON configuration and a command-line inspection/report entry point.
- Added tests that validate missing-dataset behavior and run against the real
  dataset when it is available.

## Not implemented yet

- Dataset loading, validation, preprocessing, and operator partitioning.
- Centralized or local machine-learning models.
- Node/Express APIs and MongoDB persistence.
- React pages and dashboard integration.
- Docker services and end-to-end orchestration.

## Validation

- Phase 1 structure and manifest checks: passed.
- Python TOML parsing and dependency-manifest checks: passed.
- Backend and frontend `npm install --package-lock-only --ignore-scripts`: passed.
- Backend and frontend production-only `npm audit --omit=dev --audit-level=high`: passed
  with no vulnerabilities.
- Runtime feature tests: not applicable; no runtime features are implemented.
- Phase 2 Python syntax/compile validation: passed.
- Phase 2 data-pipeline tests: `2 passed, 1 skipped`.
- Phase 2A inspection tests: `3 passed`.
- Phase 2B preprocessing and partition tests: `4 passed`.
- Phase 2C leakage audit regression tests: `5 passed`.
- Phase 3 baseline and data-pipeline tests: `6 passed`.
- Phase 4 federated and data-pipeline tests: `9 passed`.
- Threat Intelligence and regression tests: `11 passed`.
- CTI summary tests: passed.
- Backend integration tests and API validation: passed.

## Known issues

- Python and Node packages have not been installed into a runtime environment;
  Node lockfiles were generated during manifest resolution.
- The provided `train_data.txt` and `test_data.txt` files were verified as
  readable comma-delimited datasets despite their `.txt` extensions.
- Project copies were added as `train_data.csv` and `test_data.csv` under
  `data/raw/5g-intrusion` without modifying the source files or contents.
- Phase 2A inspection completed for the real train/test CSV files.
- The target column was verified as `attack`; no model training or federated
  learning was performed.
- Saved the factual inspection report to
  `data/processed/dataset_inspection_report.json`.
- Phase 2B preprocessing and partitioning completed using training-only fitting.
- Exact train/test overlap was audited using all feature columns plus `attack`.
- 1,176,079 raw training row occurrences overlapped exactly with test records.
  These correspond to 60,756 unique overlapping records and 148,070 overlapping
  test rows (76.00% of test rows); all overlapping rows had the `benign` class.
- Raw training data contains 1,753,454 rows and 489,658 unique rows, with
  1,263,796 duplicate rows beyond the unique-record count.
- The previous cleaned size of 577,375 was correct: it equals
  `1,753,454 - 1,176,079`. Training-only duplicates were not accidentally
  removed; 148,473 duplicate rows remain in the cleaned training data.
- Created the leakage-free derived training dataset at
  `data/processed/train_data_leakage_free.csv`.
- Removed all training row occurrences that exactly matched complete test
  records. Duplicates occurring only within training were retained.
- Dropped only the five Phase 2A features with at least 95% missing training
  values: `ip.fragments`, `tcp.segments`, `tcp.reassembled.length`, `udp.port`,
  and `udp.length`.
- Saved the fitted preprocessing and label-encoding artifacts, transformed test
  data, isolated IID/non-IID operator partitions, and reports under
  `data/processed`.
- Phase 3 centralized baseline completed with scikit-learn
  `SGDClassifier(loss="log_loss", class_weight="balanced", random_state=42)`.
- The model was trained on the leakage-free IID operator partitions and
  evaluated only on the untouched test transformation produced by Phase 2.
- Saved the model, experiment configuration, and evaluation results under
  `data/processed`.
- Phase 4 federated learning completed with four Flower `NumPyClient`
  clients and Flower `FedAvg` aggregation weighted by local sample count.
- Clients train only on their own saved transformed IID or non-IID operator
  partition; only `coef_` and `intercept_` are exchanged.
- A real three-round IID experiment was run and evaluated on the untouched
  test transformation. Reports and model parameters are saved under
  `data/processed`.
- Threat Intelligence layer completed using the saved federated IID model.
- Local predictions from each of the four processed operator partitions are
  converted into structured threat records; benign predictions are not emitted.
- Threat records contain only threat metadata and are propagated to the other
  three simulated operators without feature arrays, labels, or raw records.
- The generated events are explicitly labeled as simulated,
  model-generated detection events; they are not claimed to be real-time
  attacks.
- Detailed events remain available for local analysis, while
  `data/processed/threat_summary.json` is the primary backend/dashboard
  integration artifact, aggregated by operator, attack type, severity, and
  status.
- Added minimal Node.js/Express REST integration for health, system status,
  operators, federated metrics, threat summary, bounded threat listing, and
  bounded threat lookup.
- Backend reads the existing processed artifacts without adding ML or CTI
  logic. MongoDB persistence is environment-configured and stores the summary
  plus at most 1,000 detailed threat records.
- Full npm audits report transitive development-tool advisories in the
  frontend/backend dependency trees; these do not affect production-only
  dependencies at this foundation stage and should be reassessed when runtime
  code is added.

## Pending work

- Review the backend API before beginning React/dashboard integration.

Follow the phase order in `PROJECT_SPEC.md`. Do not begin a later phase until
the current phase has been implemented and tested.
