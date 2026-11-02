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

## Render deployment

The root [`render.yaml`](render.yaml) defines separate backend and static
frontend services. In Render, create a **Blueprint** from this repository and
review the two services before applying it.

For the backend service, verify:

- Root Directory: `backend`
- Runtime: Node
- Build Command: `npm ci`
- Start Command: `npm start`
- Health Check Path: `/api/health`
- `CORS_ORIGIN`: the exact deployed frontend URL, for example
  `https://your-frontend.onrender.com`

For the frontend service, verify:

- Root Directory: `frontend`
- Runtime: Static Site
- Build Command: `npm ci && npm run build`
- Publish Directory: `dist`
- `VITE_API_URL`: the exact deployed backend API base URL, for example
  `https://your-backend.onrender.com/api`

The Blueprint marks both URL variables as secret dashboard inputs. After
Render assigns the real service URLs, enter those actual URLs in the
corresponding service settings and redeploy the frontend after setting
`VITE_API_URL`. Do not guess or commit Render subdomains. The backend accepts
`PORT` from Render and binds to `0.0.0.0`; local development continues to use
`BACKEND_PORT` or port 3000 and the frontend's localhost API fallback.

## Configuration

Copy `.env.example` to `.env` for local development. Do not commit `.env` or
credentials. Configuration values are placeholders until the corresponding
services are implemented.
