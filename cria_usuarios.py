import requests

DB_URL = "http://127.0.0.1:8100"
DB_TOKEN = "dev-internal-token"

headers = {
    "x-internal-token": DB_TOKEN,
    "Content-Type": "application/json"
}

for i in range(1, 11):
    payload = {
        "name": f"Usuario {i}",
        "username": f"usuario{i}",
        "email": f"usuario{i}@email.com",
        "password": "123456"
    }

    response = requests.post(
        f"{DB_URL}/users/create",
        json=payload,
        headers=headers
    )

    if response.status_code in (200, 201):
        print(f"✅ Usuário {i} criado com sucesso!")
    else:
        print(f"❌ Erro ao criar usuário {i}: {response.status_code} - {response.text}")
