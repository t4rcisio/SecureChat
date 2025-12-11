# worker.py
import asyncio
import json
import websockets
import requests
import sys

GATEWAY_HTTP = "http://127.0.0.1:8000"
GATEWAY_WS = "ws://127.0.0.1:8000/ws"
PASSWORD = "123456"


async def simulate_user(username, target):
    # LOGIN
    r = requests.post(f"{GATEWAY_HTTP}/login", json={
        "username": username,
        "password": PASSWORD
    })

    if r.status_code != 200:
        print(f"[{username}] ❌ Falha no login")
        return

    print(f"[{username}] ✔ Login OK")

    # CONNECT WS
    try:
        ws = await websockets.connect(f"{GATEWAY_WS}/{username}")
        print(f"[{username}] 🔌 WebSocket conectado")
    except Exception as e:
        print(f"[{username}] ❌ Erro ao conectar WS: {e}")
        return

    # ENVIAR MENSAGEM
    payload = {
        "sender": username,
        "receiver": target,
        "content": f"Olá {target}, aqui é {username}!"
    }

    resp = requests.post(f"{GATEWAY_HTTP}/send", json=payload)
    if resp.status_code == 200:
        print(f"[{username}] 📤 Enviou mensagem para {target}")
    else:
        print(f"[{username}] ❌ Erro ao enviar")

    # RECEBER
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout=10)
        print(f"[{username}] 📩 Recebeu: {msg}")
    except asyncio.TimeoutError:
        print(f"[{username}] ⏳ Não recebeu nenhuma mensagem")

    await ws.close()


if __name__ == "__main__":
    username = sys.argv[1]
    target = sys.argv[2]
    asyncio.run(simulate_user(username, target))
