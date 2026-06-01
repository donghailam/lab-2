from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import os

import firebase_admin
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from firebase_admin import auth, credentials, firestore
from pydantic import BaseModel, Field


def get_service_account_path() -> Path:
    configured_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return Path(__file__).resolve().parent / "serviceAccountKey.json"


def create_firestore_client():
    service_account_path = get_service_account_path()
    if not service_account_path.exists():
        raise RuntimeError(
            "Missing Firebase service account file. Set FIREBASE_SERVICE_ACCOUNT_PATH "
            "or place serviceAccountKey.json inside backend/."
        )

    cred = credentials.Certificate(str(service_account_path))
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    return firestore.client()


def get_allowed_origins() -> list[str]:
    raw_origins = os.getenv(
        "CORS_ALLOW_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500",
    )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app = FastAPI(title="Firebase Chatbot API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
db = create_firestore_client()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


def require_bearer_token(authorization: Optional[str]) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must use Bearer token.",
        )
    return token


def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    token = require_bearer_token(authorization)
    try:
        return auth.verify_id_token(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token.",
        ) from exc


def serialize_message(message: Dict[str, Any]) -> Dict[str, Any]:
    created_at = message.get("created_at")
    if isinstance(created_at, datetime):
        message["created_at"] = created_at.astimezone(timezone.utc).isoformat()
    return message


@app.get("/")
def root():
    return {"message": "Firebase chatbot API is running."}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/auth/me")
def auth_me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "uid": current_user["uid"],
        "email": current_user.get("email"),
        "name": current_user.get("name"),
    }


@app.post("/chat")
def chat(req: ChatRequest, current_user: Dict[str, Any] = Depends(get_current_user)):
    user_message = req.message.strip()
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message must not be empty.",
        )

    reply = f"Bot: I received '{user_message}'."
    message = {
        "uid": current_user["uid"],
        "email": current_user.get("email"),
        "user_message": user_message,
        "bot_reply": reply,
        "created_at": datetime.now(timezone.utc),
    }
    saved_ref = db.collection("messages").add(message)[1]

    response_message = serialize_message({**message, "id": saved_ref.id})
    return {"reply": reply, "message": response_message}


@app.get("/messages")
def get_messages(
    limit: int = Query(default=50, ge=1, le=100),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    records = []
    docs = db.collection("messages").where("uid", "==", current_user["uid"]).stream()

    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        records.append(item)

    records.sort(
        key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc)
    )
    records = records[-limit:]
    return {"messages": [serialize_message(item) for item in records]}
