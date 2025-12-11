import asyncio
import json
import websockets
import requests

GATEWAY_HTTP = "http://127.0.0.1:8000"
GATEWAY_WS = "ws://127.0.0.1:8000/ws"

# Usuários existentes no banco
USERS = [f"usuario{i}" for i in range(1, 11)]
PASSWORD = "123456"


async def simulate_user(username):
    # 1. LOGIN
    r = requests.post(f"{GATEWAY_HTTP}/login", json={
        "username": username,
        "password": PASSWORD
    })

    if r.status_code != 200:
        print(f"❌ Falha no login: {username}")
        return

    print(f"✔ Login OK para {username}")

    # 2. CONECTAR AO WEBSOCKET DO GATEWAY
    try:
        ws = await websockets.connect(f"{GATEWAY_WS}/{username}")
    except Exception as e:
        print(f"❌ Erro ao conectar WebSocket para {username}: {e}")
        return

    print(f"🔌 {username} conectado ao WebSocket")

    # 3. DEFINIR DESTINO (sempre um usuário válido)
    index = USERS.index(username)
    target = USERS[(index + 1) % len(USERS)]
    # 4. ENVIAR UMA MENSAGEM PELO GATEWAY
    payload = {
        "sender": username,
        "receiver": target,
        "content": f"Olá, aqui é {username}!"
    }

    resp = requests.post(f"{GATEWAY_HTTP}/send", json=payload)

    if resp.status_code == 200:
        print(f"📤 {username} enviou mensagem para {target}")
    else:
        print(f"❌ {username} falhou ao enviar mensagem: {resp.text}")

    # 5. TENTAR RECEBER NOTIFICAÇÃO (com timeout)
    try:
        msg = await asyncio.wait_for(ws.recv(), timeout=5)
        print(f"📩 {username} recebeu: {msg}")
    except asyncio.TimeoutError:
        print(f"⏳ {username} não recebeu nenhuma mensagem")

    await ws.close()


async def main():
    # Executa todos usuários simultaneamente
    tasks = [simulate_user(u) for u in USERS]
    await asyncio.gather(*tasks)


asyncio.run(main())
