# db_service.py
import os
from fastapi import FastAPI, HTTPException, Header, Depends
from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from passlib.context import CryptContext

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# CONFIG
DB_FILE = os.environ.get("DB_FILE", "./users.db")
DATABASE_URL = f"sqlite:///{DB_FILE}"
INTERNAL_TOKEN = os.environ.get("DB_INTERNAL_TOKEN", "dev-internal-token")  # shared secret for internal calls

# DB setup
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# SQLAlchemy model
class UserDB(Base):
    __tablename__ = "users"
    username = Column(String, primary_key=True, index=True)  # PK non-editable
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # hashed password

    private_key = Column(String, nullable=False)
    public_key = Column(String, nullable=False)

    contacts = Column(JSON, nullable=False)

Base.metadata.create_all(bind=engine)

# Pydantic schemas (requests/responses)
class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

class UserOut(BaseModel):
    name: str
    username: str
    public_key: str

class ValidateRequest(BaseModel):
    username: str
    password: str

class ValidateResponse(BaseModel):
    ok: bool
    username: Optional[str] = None
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    public_key: Optional[str] = None
    private_key: Optional[str] = None

    contacts: Optional[Dict[str, Any]] = None

# FastAPI app
app = FastAPI(title="DB Service")

# Dependency to check internal token header
def require_internal_token(x_internal_token: str = Header(None)):
    if x_internal_token != INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized: invalid internal token")
    return True

# Helpers
import hashlib
import bcrypt
import base64

def __encrypt_password(str_input: str) -> bytes:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(str_input.encode('utf-8'), salt)
    return hashed

def hash_password(password: str):
    pass_bytes = __encrypt_password(password)
    hash_str = base64.b64encode(pass_bytes).decode("utf-8")

    return hash_str

def verify_password(plain: str, hashed: str) -> bool:

    hash_bytes = base64.b64decode(hashed)
    return bcrypt.checkpw(plain.encode('utf-8'), hash_bytes)


# Routes (protected by internal token)
@app.post("/users/create", response_model=UserOut, dependencies=[Depends(require_internal_token)])
def create_user(data: UserCreate):
    db = SessionLocal()
    try:
        # username exists?
        if db.query(UserDB).filter(UserDB.username == data.username).first():
            raise HTTPException(400, detail="Username já existe")

        # email unique?
        if db.query(UserDB).filter(UserDB.email == data.email).first():
            raise HTTPException(400, detail="Email já cadastrado")


        hashed = hash_password(data.password)

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_key = private_key.public_key()

        private_key_str = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")

        public_key_str = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        user = UserDB(username=data.username, name=data.name, email=data.email, password=hashed, public_key=public_key_str, private_key=private_key_str, contacts={})
        db.add(user)
        db.commit()
        db.refresh(user)
        return UserOut(name=user.name, username=user.username, public_key=user.public_key)
    finally:
        db.close()

@app.put("/users/{username}", response_model=UserOut, dependencies=[Depends(require_internal_token)])
def update_user(username: str, data: UserUpdate):
    """
    Username é PK e não pode ser alterado.
    Só atualiza os campos enviados (name, email, password).
    Garante que email permaneça único.
    """
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if not user:
            raise HTTPException(404, detail="Usuário não encontrado")

        if data.email and data.email != user.email:
            # verify unique email
            if db.query(UserDB).filter(UserDB.email == data.email, UserDB.username != username).first():
                raise HTTPException(400, detail="Email já está em uso por outro usuário")
            user.email = data.email

        if data.name:
            user.name = data.name



        if data.password:
            user.password = hash_password(data.password)

        db.commit()
        db.refresh(user)
        return UserOut(name=user.name, username=user.username, email=user.email)

    finally:
        db.close()

@app.delete("/users/{username}", response_model=dict, dependencies=[Depends(require_internal_token)])
def delete_user(username: str):
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if not user:
            raise HTTPException(404, detail="Usuário não encontrado")
        db.delete(user)
        db.commit()
        return {"ok": True, "message": "Usuário removido"}
    finally:
        db.close()

@app.get("/users/{username}", response_model=UserOut, dependencies=[Depends(require_internal_token)])
def get_user(username: str):
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.username == username).first()
        if not user:
            raise HTTPException(404, detail="Usuário não encontrado")
        return UserOut(name=user.name, username=user.username, public_key=user.public_key)
    finally:
        db.close()

@app.post("/users/validate", response_model=ValidateResponse, dependencies=[Depends(require_internal_token)])
def validate_user(data: ValidateRequest):
    """
    Valida credenciais. Retorna ok:True e dados do usuário (sem senha) se estiver ok.
    """
    db = SessionLocal()
    try:
        user = db.query(UserDB).filter(UserDB.username == data.username).first()
        if not user:
            return ValidateResponse(ok=False)
        if not verify_password(data.password, user.password):
            return ValidateResponse(ok=False)
        return ValidateResponse(ok=True, username=user.username, name=user.name, email=user.email, public_key=user.public_key, private_key=user.private_key, contacts=user.contacts)
    finally:
        db.close()


def run_db_service():
    import uvicorn
    uvicorn.run("db_service:app", host="127.0.0.1", port=8100, reload=True)

if __name__ == "__main__":
    run_db_service()



