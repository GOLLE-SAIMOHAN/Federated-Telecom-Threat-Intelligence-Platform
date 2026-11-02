# Federated Telecom Threat Intelligence Platform

This repository contains a research prototype for privacy-preserving,
collaborative telecom threat detection using simulated operators, federated
learning, cyber threat intelligence, and a web dashboard.

The authoritative requirements are in [`PROJECT_SPEC.md`](PROJECT_SPEC.md).
This project is not a production telecom network controller or a production
security platform.

## Repository status

The local ML experiment set and a read-only React/Express demonstration are
implemented. The dashboard uses a tracked snapshot derived from the generated
experiment reports, so it can run without copying raw datasets or model
binaries into the application. See
[`IMPLEMENTATION_STATUS.md`](IMPLEMENTATION_STATUS.md) for validation results.

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

Use Python 3.11 with the project virtual environment and pinned dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Node.js

Install Node.js 20 or newer, then install each JavaScript workspace:

```powershell
Set-Location backend
npm ci
Set-Location ..\frontend
npm ci
```

### Run the local demo

Start the backend in one terminal:

```powershell
Set-Location backend
npm start
```

Start the frontend in another terminal:

```powershell
Set-Location frontend
$env:VITE_API_URL = "http://localhost:3000/api"
npm run dev
```

Open `http://localhost:5173`. The backend API is available at
`http://localhost:3000/api`, including `/health`, `/system/status`,
`/centralized`, `/federated`, `/experiments`, `/operators`, and the honest
empty-state threat endpoints.

## Configuration

Copy `.env.example` to `.env` for local development. Do not commit `.env` or
credentials. Configuration values are placeholders until the corresponding
services are implemented.
