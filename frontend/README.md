# ScreenPilot Frontend

React + TypeScript + Vite + Tailwind CSS SPA for configuring tasks, starting runs, and viewing a control-room style live replay (timeline logs, visual evidence, screenshot stage, and run summary).

## Setup

```bash
npm install
```

Copy `.env.example` to `.env` and set `VITE_BACKEND_BASE_URL` to your running backend (e.g. `http://127.0.0.1:8000` for local dev).

Backend planner mode can be switched with:
- `ACTION_PLANNER_MODE=json_schema` (legacy JSON action planner)
- `ACTION_PLANNER_MODE=computer_use` (official Computer Use tool-calling path with bounded fallback)

## Run backend first

Start the ScreenPilot backend before using the frontend. See the project root docs:

- [Run the backend (quick reference)](../docs/run-backend-quick.md) – in_memory vs GCP mode, `./backend/run_dev.sh`.

## Develop

```bash
npm run dev
```

## Persona-focused UX features

- Live timeline cards with explicit Decision / Why / Action / Outcome sections.
- Live screenshot stage with latest capture and a mini filmstrip.
- Confirmation modal with irreversible-action warning and screenshot context.
- Terminal run summary with duration, step count, and failure count.

## Build

```bash
npm run build
```

## Preview production build

```bash
npm run preview
```
