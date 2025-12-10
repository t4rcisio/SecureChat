from fastapi import FastAPI, WebSocket, Depends
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, case, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel
from typing import Dict
from datetime import datetime

# ==========================
# ✅ CONFIGURAÇÃO DO BANCO
# ==========================

DATABASE_URL = "sqlite:///./chat.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ==========================
# ✅ MODELO DA TABELA
# ==========================

class MessageDB(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String, index=True)
    receiver = Column(String, index=True)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ==========================
# ✅ SCHEMAS Pydantic
# ==========================

class MessageCreate(BaseModel):
    sender: str
    receiver: str
    content: str

class MessageOut(BaseModel):
    sender: str
    receiver: str
    content: str
    timestamp: datetime

# ==========================
# ✅ FASTAPI APP
# ==========================

app = FastAPI()
connections: Dict[str, WebSocket] = {}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================
# ✅ WEBSOCKET - TEMPO REAL
# ==========================

@app.websocket("/ws/{username}")
async def websocket_endpoint(ws: WebSocket, username: str):
    await ws.accept()
    connections[username] = ws
    try:
        while True:
            await ws.receive_text()
    except:
        connections.pop(username, None)

# ==========================
# ✅ ENVIAR MENSAGEM
# ==========================

@app.post("/messages/send")
async def send_message(msg: MessageCreate, db: Session = Depends(get_db)):
    message = MessageDB(
        sender=msg.sender,
        receiver=msg.receiver,
        content=msg.content,
        timestamp=datetime.now()
    )

    db.add(message)
    db.commit()

    # ✅ Envio em tempo real
    if msg.receiver in connections:
        await connections[msg.receiver].send_json({
            "sender": msg.sender,
            "content": msg.content,
            "timestamp": message.timestamp.isoformat()
        })

    return {"status": "ok"}

# ==========================
# ✅ BUSCAR HISTÓRICO
# ==========================

@app.get("/messages/history/{user1}/{user2}")
async def get_history(user1: str, user2: str, db: Session = Depends(get_db)):
    messages = db.query(MessageDB).filter(
        ((MessageDB.sender == user1) & (MessageDB.receiver == user2)) |
        ((MessageDB.sender == user2) & (MessageDB.receiver == user1))
    ).order_by(MessageDB.timestamp).all()

    return messages

@app.get("/messages/conversations/{username}")
def get_conversations(username: str, db: Session = Depends(get_db)):

    # Determina quem é o "outro usuário" na conversa
    other_user = case(
        (MessageDB.sender == username, MessageDB.receiver),
        else_=MessageDB.sender
    )

    results = (
        db.query(
            other_user.label("contact"),
            func.max(MessageDB.timestamp).label("last_time")
        )
        .filter(
            (MessageDB.sender == username) |
            (MessageDB.receiver == username)
        )
        .group_by("contact")
        .order_by(func.max(MessageDB.timestamp).desc())
        .all()
    )

    # Formata no padrão solicitado: [[nome, datetime], ...]
    return [[r.contact, r.last_time.isoformat()] for r in results]


def run_db_service():
    import uvicorn
    uvicorn.run("message_service:app", host="127.0.0.1", port=9100, reload=True)

if __name__ == "__main__":
    run_db_service()