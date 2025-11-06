```markdown
# Vyoma Backend (FastAPI) — Hologram Config API & WebSocket

What this scaffold provides
- REST API to list drones and get/update hologram configuration:
  - GET /api/drones
  - GET /api/drones/{key}
  - POST /api/drones/{key}/update  (body: style, color, scale, animate, simulator)
- WebSocket endpoint to receive and broadcast real-time updates:
  - ws://<host>/ws
  - Clients send JSON messages like {"type":"update","key":"quadcopter","payload":{...}}
  - Server broadcasts updates to all connected clients as {"type":"update","key":...,"payload":...}
- Static file hosting: put your frontend HTML+assets in `app/static/` and open http://localhost:8000/
- Uses SQLite + SQLModel for quick persistence (file: data.db)

Requirements
- Python 3.10+
- Install deps: pip install -r requirements.txt

Run (development)
1. Create venv and install:
   python -m venv .venv
   source .venv/bin/activate   # or .venv\Scripts\activate on Windows
   pip install -r requirements.txt

2. Start server:
   uvicorn app.main:app --reload --port 8000

3. Open your frontend:
   - If you placed your HTML in app/static/, open http://localhost:8000/
   - Or point your existing frontend to API at http://localhost:8000/api/ and ws://localhost:8000/ws

Notes & next steps
- Add authentication/authorization (JWT) for saving edits and WebSocket auth.
- If you want to store telemetry or versioned model assets, add additional DB models and endpoints.
- For production, use Postgres, run behind a server (uvicorn/gunicorn), enable TLS, and configure CORS properly.
```