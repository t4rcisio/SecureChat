# auth_service.py
import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jose import jwt
from datetime import datetime, timedelta

# CONFIG
DB_SERVICE_URL = os.environ.get("DB_SERVICE_URL", "http://localhost:8100")  # endpoint do DB Service
INTERNAL_TOKEN = os.environ.get("DB_INTERNAL_TOKEN", "dev-internal-token")  # deve ser igual ao DB service
SECRET_KEY = os.environ.get("AUTH_SECRET_KEY", "MEGA_SECRET_KEY_CHANGE_THIS")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Pydantic models (same shapes as before)
class User(BaseModel):
    name: str
    username: str  # Primary Key - não editável após a criação
    email: str
    password: str

class Login(BaseModel):
    username: str
    password: str

app = FastAPI(title="Auth Service")

# HTTP client (sync via httpx)
client = httpx.Client(timeout=10.0)

def create_jwt(username: str):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

def internal_headers():
    return {"X-Internal-Token": INTERNAL_TOKEN, "Content-Type": "application/json"}

# Routes (these mirror your previous endpoints: /new, /edit, /delete, /login)

@app.post("/new")
def create_user(data: User):
    # chama DB Service
    url = f"{DB_SERVICE_URL}/users/create"
    resp = client.post(url, json=data.dict(), headers=internal_headers())
    if resp.status_code != 200:
        # propaga erro com mensagem legível
        try:
            detail = resp.json().get("detail") or resp.text
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=f"DB Service: {detail}")
    return {"status": "ok", "message": "Usuário criado", "user": resp.json()}

@app.post("/edit")
def edit_user(data: User):
    # username não pode ser alterado; chamamos PUT /users/{username}
    url = f"{DB_SERVICE_URL}/users/{data.username}"
    payload = {"name": data.name, "email": data.email, "password": data.password}
    resp = client.put(url, json=payload, headers=internal_headers())
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail") or resp.text
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=f"DB Service: {detail}")
    return {"status": "ok", "message": "Usuário atualizado", "user": resp.json()}

@app.post("/delete")
def delete_user(username: str):
    url = f"{DB_SERVICE_URL}/users/{username}"
    resp = client.delete(url, headers=internal_headers())
    if resp.status_code != 200:
        try:
            detail = resp.json().get("detail") or resp.text
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=f"DB Service: {detail}")
    return {"status": "ok", "message": "Usuário deletado"}

@app.post("/login")
def login(data: Login):
    url = f"{DB_SERVICE_URL}/users/validate"
    resp = client.post(url, json=data.dict(), headers=internal_headers())
    if resp.status_code != 200:
        # DB service sempre responde 200 com {ok:True/False} — mas verificamos
        raise HTTPException(status_code=500, detail="Erro ao contatar DB Service")
    body = resp.json()
    if not body.get("ok"):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")
    # sucesso → gerar JWT
    token = create_jwt(body.get("username"))
    return {"access_token": token, "token_type": "bearer", "user": {"username": body.get("username"), "name": body.get("name"), "email": body.get("email")}}




