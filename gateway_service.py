# gateway_service.py
import asyncio
import json
import requests
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict

import websockets

# ================================================
# CONFIG
# ================================================
DB_SERVICE_URL = "http://127.0.0.1:8100"
MSG_SERVICE_URL = "http://127.0.0.1:9100"
INTERNAL_TOKEN = "dev-internal-token"

# Conexões WebSocket do cliente (PyQt)
active_ws: Dict[str, WebSocket] = {}

app = FastAPI(title="Gateway Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================
# HELPERS
# ================================================
def db_post(path: str, payload: dict):
    try:
        return requests.post(
            DB_SERVICE_URL + path,
            json=payload,
            headers={"x-internal-token": INTERNAL_TOKEN},
            timeout=5
        )
    except Exception as e:
        raise HTTPException(500, f"Erro comunicando com db_service: {e}")

def db_get(path: str):
    try:
        return requests.get(
            DB_SERVICE_URL + path,
            headers={"x-internal-token": INTERNAL_TOKEN},
            timeout=5
        )
    except Exception as e:
        raise HTTPException(500, f"Erro comunicando com db_service: {e}")

def msg_post(path: str, payload: dict):
    try:
        return requests.post(MSG_SERVICE_URL + path, json=payload, timeout=5)
    except Exception as e:
        raise HTTPException(500, f"Erro comunicando com message_service: {e}")

def msg_get(path: str):
    try:
        return requests.get(MSG_SERVICE_URL + path, timeout=5)
    except Exception as e:
        raise HTTPException(500, f"Erro comunicando com message_service: {e}")

# ================================================
# USER ROUTES
# ================================================
@app.post("/register")
def register_user(data: dict):
    r = db_post("/users/create", data)
    if r.status_code != 200:
        raise HTTPException(status_code=400, detail=r.json())
    return r.json()

@app.post("/login")
def login(data: dict):
    r = db_post("/users/validate", data)
    result = r.json()

    if not result.get("ok"):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    return result

# ================================================
# MESSAGE ROUTES
# ================================================
@app.get("/conversations/{username}")
def conversations(username: str):
    return msg_get(f"/messages/conversations/{username}").json()

@app.get("/user/{username}")
def get_user(username: str):
    return db_get(f"/users/{username}").json()

@app.get("/history/{u1}/{u2}")
def history(u1: str, u2: str):
    return msg_get(f"/messages/history/{u1}/{u2}").json()

@app.post("/send")
def send_message(payload: dict):
    return msg_post("/messages/send", payload).json()

# ================================================
# WEBSOCKET RELAY
# ================================================
async def connect_to_message_service(username: str):
    """
    Tenta conectar ao message_service via WebSocket.
    Repetirá até conseguir (importante para escalabilidade).
    """
    url = f"ws://127.0.0.1:9100/ws/{username}"

    while True:
        try:
            ws = await websockets.connect(url)
            print(f"[GATEWAY] Conectado ao message_service como {username}")
            return ws
        except Exception:
            print("[GATEWAY] message_service indisponível. Tentando novamente em 1s...")
            await asyncio.sleep(1)

@app.websocket("/ws/{username}")
async def websocket_handler(ws: WebSocket, username: str):
    await ws.accept()
    active_ws[username] = ws
    print(f"[GATEWAY] {username} conectado (cliente).")

    backend_ws = await connect_to_message_service(username)

    async def from_ui_to_backend():
        while True:
            try:
                msg = await ws.receive_text()
                await backend_ws.send(msg)
            except Exception:
                break

    async def from_backend_to_ui():
        while True:
            try:
                backend_msg = await backend_ws.recv()
                await ws.send_text(backend_msg)
            except Exception:
                break

    try:
        await asyncio.gather(
            from_ui_to_backend(),
            from_backend_to_ui()
        )
    except Exception:
        pass
    finally:
        print(f"[GATEWAY] {username} desconectado.")
        active_ws.pop(username, None)

        try:
            await backend_ws.close()
        except:
            pass

# ================================================
def run_gateway():
    import uvicorn
    uvicorn.run("gateway_service:app", host="127.0.0.1", port=8000, reload=False)

if __name__ == "__main__":
    run_gateway()
