from fastapi import FastAPI
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
import os

app = FastAPI()

# Firebase init
cred_path = os.path.join(os.path.dirname(__file__), "../frontend/serviceAccountKey.json")
cred = credentials.Certificate(cred_path)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Model
class ChatRequest(BaseModel):
    message: str

# API test
@app.get("/")
def root():
    return {"message": "API running"}

@app.get("/health")
def health():
    return {"status": "ok"}

# Chat
@app.post("/chat")
def chat(req: ChatRequest):
    reply = "Bot: " + req.message

    db.collection("messages").add({
        "user_message": req.message,
        "bot_reply": reply
    })

    return {"reply": reply}

# Get messages
@app.get("/messages")
def get_messages():
    docs = db.collection("messages").stream()
    return [doc.to_dict() for doc in docs]
