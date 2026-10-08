# Federated Telecom Threat Intelligence Platform

This repository contains a research prototype for privacy-preserving,
collaborative telecom threat detection using simulated operators, federated
learning, cyber threat intelligence, and a web dashboard.

The authoritative requirements are in [`PROJECT_SPEC.md`](PROJECT_SPEC.md).
This project is not a production telecom network controller or a production
security platform.

## Repository status

Phase 1 (project foundation) is complete. Runtime features are intentionally
not implemented yet. See [`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md)
for the current scope and validation results.

## Planned structure

- `ml/` — dataset processing, models, evaluation, and experiments
- `operators/` — isolated simulated operator environments
- `federated-server/` — Flower coordinator
- `backend/` — Node.js/Express application API
- `frontend/` — React dashboard
- `database/` — MongoDB-related initialization and documentation
- `docker/` — container-related configuration

## Initial setup

### Python

Use Python 3.11 or newer within the supported Python 3 series, create a
virtual environment, and install the pinned top-level dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Node.js

Install Node.js 20 or newer, then install each JavaScript workspace's
dependencies when that workspace is implemented:

```powershell
Set-Location backend
npm install
Set-Location ..\frontend
npm install
```

The backend and frontend manifests currently declare only their phase-specific
foundation dependencies. Their application entry points will be added in later
phases.

## Configuration

Copy `.env.example` to `.env` for local development. Do not commit `.env` or
credentials. Configuration values are placeholders until the corresponding
services are implemented.
