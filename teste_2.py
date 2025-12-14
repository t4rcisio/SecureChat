import asyncio
import time
import statistics
import requests
import websockets
import matplotlib.pyplot as plt

GATEWAY_HTTP = "http://127.0.0.1:8000"
GATEWAY_WS = "ws://127.0.0.1:8000/ws"
PASSWORD = "123456"


async def simulate_user(username, users, metrics):
    # -------- LOGIN --------
    t0 = time.perf_counter()
    r = requests.post(f"{GATEWAY_HTTP}/login", json={
        "username": username,
        "password": PASSWORD
    })
    metrics["login"].append(time.perf_counter() - t0)

    if r.status_code != 200:
        return

    # -------- WS CONNECT --------
    ws = await websockets.connect(f"{GATEWAY_WS}/{username}")

    target = users[(users.index(username) + 1) % len(users)]

    # -------- SEND MESSAGE --------
    payload = {
        "sender": username,
        "receiver": target,
        "content": f"Olá de {username}"
    }

    t1 = time.perf_counter()
    requests.post(f"{GATEWAY_HTTP}/send", json=payload)
    metrics["send"].append(time.perf_counter() - t1)

    # -------- RECEIVE --------
    try:
        t2 = time.perf_counter()
        await asyncio.wait_for(ws.recv(), timeout=5)
        metrics["recv"].append(time.perf_counter() - t2)
    except asyncio.TimeoutError:
        pass

    await ws.close()


async def run_test(n_users):
    users = [f"usuario{i}" for i in range(1, n_users + 1)]
    metrics = {"login": [], "send": [], "recv": []}

    tasks = [simulate_user(u, users, metrics) for u in users]
    await asyncio.gather(*tasks)

    return {
        "login": statistics.mean(metrics["login"]),
        "send": statistics.mean(metrics["send"]),
        "recv": statistics.mean(metrics["recv"])
    }


async def main():
    cargas = [5, 10, 20, 40]

    login_avg = []
    send_avg = []
    recv_avg = []

    for c in cargas:
        print(f"🔎 Testando com {c} usuários...")
        r = await run_test(c)
        login_avg.append(r["login"])
        send_avg.append(r["send"])
        recv_avg.append(r["recv"])

    # -------- GRÁFICOS --------

    plt.figure()
    plt.plot(cargas, login_avg, marker='o')
    plt.xlabel("Usuários simultâneos")
    plt.ylabel("Tempo médio (s)")
    plt.title("Teste 1 – Responsividade do Login")
    plt.show()

    plt.figure()
    plt.plot(cargas, send_avg, marker='o')
    plt.xlabel("Usuários simultâneos")
    plt.ylabel("Tempo médio (s)")
    plt.title("Teste 2 – Latência de Envio de Mensagens")
    plt.show()

    plt.figure()
    plt.plot(cargas, recv_avg, marker='o')
    plt.xlabel("Usuários simultâneos")
    plt.ylabel("Tempo médio (s)")
    plt.title("Teste 3 – Latência WebSocket (Escalabilidade)")
    plt.show()


asyncio.run(main())
