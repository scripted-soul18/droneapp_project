from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
import json
from sqlmodel import Session, select
from app.app.db import init_db, engine
import models
from app.schemas import DroneConfigUpdate, DroneConfigOut
import asyncio

app = FastAPI(title="Vyoma Hologram Backend")

# initialize DB and seed defaults
init_db()

# mount static folder - put your frontend (html + js + assets) into app/static
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# simple in-memory WebSocket manager for broadcasting
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        async with self.lock:
            self.active.append(ws)

    async def disconnect(self, ws: WebSocket):
        async with self.lock:
            if ws in self.active:
                self.active.remove(ws)

    async def broadcast(self, message: Dict):
        data = json.dumps(message)
        async with self.lock:
            coros = [ws.send_text(data) for ws in self.active]
        if coros:
            await asyncio.gather(*coros, return_exceptions=True)

manager = ConnectionManager()

# REST endpoints
@app.get("/api/drones", response_model=List[DroneConfigOut])
def list_drones():
    with Session(engine) as session:
        drones = session.exec(select(models.DroneConfig)).all()
        return drones

@app.get("/api/drones/{key}", response_model=DroneConfigOut)
def get_drone(key: str):
    with Session(engine) as session:
        d = session.get(models.DroneConfig, key)
        if not d:
            raise HTTPException(status_code=404, detail="Drone not found")
        return d

@app.post("/api/drones/{key}/update", response_model=DroneConfigOut)
async def update_drone(key: str, payload: DroneConfigUpdate):
    with Session(engine) as session:
        d = session.get(models.DroneConfig, key)
        if not d:
            raise HTTPException(status_code=404, detail="Drone not found")
        updated = False
        data = payload.dict(exclude_none=True)
        for k, v in data.items():
            setattr(d, k, v)
            updated = True
        if updated:
            session.add(d)
            session.commit()
            session.refresh(d)
            # broadcast change to WebSocket clients
            await manager.broadcast({"type": "update", "key": key, "payload": data})
        return d

# Simple route to serve index (if you place your HTML as app/static/index.html)
@app.get("/", response_class=HTMLResponse)
def root():
    import os
    index_path = "app/static/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return HTMLResponse("<html><body><h3>Place your frontend in app/static/ and name it index.html</h3></body></html>")

# WebSocket endpoint for live updates
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            text = await ws.receive_text()
            # expect JSON messages
            try:
                msg = json.loads(text)
            except Exception:
                await ws.send_text(json.dumps({"type": "error", "detail": "invalid json"}))
                continue

            # if a client sends update messages, optionally apply them to DB as well
            # message format: { "type": "update", "key": "...", "payload": {...}, "persist": true }
            if msg.get("type") == "update" and "key" in msg and "payload" in msg:
                key = msg["key"]
                payload = msg["payload"]
                persist = msg.get("persist", False)
                if persist:
                    # apply to DB (simple, no validation here)
                    with Session(engine) as session:
                        d = session.get(models.DroneConfig, key)
                        if d:
                            for k, v in payload.items():
                                if hasattr(d, k):
                                    setattr(d, k, v)
                            session.add(d); session.commit(); session.refresh(d)
                            # broadcast the persisted update
                            await manager.broadcast({"type": "update", "key": key, "payload": payload})
                        else:
                            await ws.send_text(json.dumps({"type":"error","detail":"drone not found"}))
                else:
                    # just broadcast to other clients (ephemeral)
                    await manager.broadcast({"type": "update", "key": key, "payload": payload})
            else:
                # echo or ignore other message types
                await manager.broadcast({"type": "message", "data": msg})
    except WebSocketDisconnect:
        await manager.disconnect(ws)