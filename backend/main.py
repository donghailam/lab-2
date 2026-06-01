from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import ast
import operator
import os

import firebase_admin
from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
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
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


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


def load_recent_messages(uid: str, limit: int = 6) -> list[Dict[str, Any]]:
    records = []
    docs = db.collection("messages").where("uid", "==", uid).stream()

    for doc in docs:
        item = doc.to_dict()
        item["id"] = doc.id
        records.append(item)

    records.sort(
        key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc)
    )
    return records[-limit:]


def eval_math_expression(expression: str) -> Optional[float]:
    sanitized = expression.replace("^", "**").strip()

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in ALLOWED_OPERATORS:
            left = _eval(node.left)
            right = _eval(node.right)
            return ALLOWED_OPERATORS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in ALLOWED_OPERATORS:
            operand = _eval(node.operand)
            return ALLOWED_OPERATORS[type(node.op)](operand)
        raise ValueError("Unsupported expression")

    try:
        parsed = ast.parse(sanitized, mode="eval")
        result = _eval(parsed.body)
        return float(result)
    except Exception:
        return None


def detect_math_request(message: str) -> Optional[str]:
    candidate = message.lower().replace("=", " ").strip()
    normalized = (
        candidate.replace("tính", "")
        .replace("bao nhiêu", "")
        .replace("bằng mấy", "")
        .replace("là bao nhiêu", "")
        .strip()
    )
    allowed_chars = set("0123456789+-*/().%^ ")
    if normalized and all(char in allowed_chars for char in normalized):
        value = eval_math_expression(normalized)
        if value is not None:
            if value.is_integer():
                return f"Kết quả là {int(value)}."
            return f"Kết quả là {value:.4f}".rstrip("0").rstrip(".") + "."
    return None


def build_context_summary(recent_messages: list[Dict[str, Any]]) -> str:
    if not recent_messages:
        return ""

    latest = recent_messages[-1]["user_message"]
    return f"Trước đó bạn vừa nói về: \"{latest}\". "


def generate_reply(user_message: str, recent_messages: list[Dict[str, Any]]) -> str:
    message = user_message.strip()
    lowered = message.lower()
    context = build_context_summary(recent_messages[:-1] if recent_messages else [])

    math_reply = detect_math_request(message)
    if math_reply:
        return math_reply

    if any(keyword in lowered for keyword in ["xin chào", "chào", "hello", "hi "]):
        return (
            f"{context}Chào bạn. Mình có thể trả lời câu hỏi ngắn, giải thích ý tưởng, "
            "gợi ý các bước làm hoặc tính toán cơ bản."
        )

    if any(keyword in lowered for keyword in ["bạn làm được gì", "mày làm được gì", "help", "giúp gì"]):
        return (
            "Mình hỗ trợ tốt nhất ở 4 kiểu: "
            "1) giải thích ngắn một khái niệm, "
            "2) tóm tắt hoặc lập kế hoạch từng bước, "
            "3) so sánh 2 lựa chọn, "
            "4) tính toán biểu thức cơ bản. "
            "Bạn cứ hỏi thẳng mục tiêu."
        )

    if any(keyword in lowered for keyword in ["so sánh", "khác gì", "nên chọn"]):
        return (
            f"{context}Để so sánh gọn mà hữu ích, bạn nên nhìn theo 3 tiêu chí: "
            "mục tiêu dùng, độ phức tạp triển khai, và chi phí/rủi ro vận hành. "
            "Nếu bạn đưa 2 lựa chọn cụ thể, mình sẽ so sánh từng ý."
        )

    if any(keyword in lowered for keyword in ["kế hoạch", "lộ trình", "các bước", "bắt đầu từ đâu"]):
        return (
            f"{context}Bạn có thể bắt đầu theo thứ tự: "
            "1) chốt mục tiêu đầu ra, "
            "2) chia thành các bước nhỏ có thể kiểm tra được, "
            "3) làm phần lõi trước, "
            "4) kiểm thử lại với dữ liệu thật. "
            "Nếu muốn, mình có thể tách tiếp thành checklist cụ thể."
        )

    if lowered.endswith("?") or any(
        keyword in lowered for keyword in ["là gì", "tại sao", "vì sao", "như thế nào", "giải thích"]
    ):
        return (
            f"{context}Theo cách hiểu đơn giản, {message.rstrip('?')} "
            "là một vấn đề nên nhìn theo mục tiêu, đầu vào, cách xử lý và kết quả đầu ra. "
            "Nếu bạn muốn, mình có thể giải thích theo kiểu ngắn gọn hoặc ví dụ thực tế."
        )

    return (
        f"{context}Mình đã nhận nội dung: \"{message}\". "
        "Nếu bạn muốn câu trả lời hữu ích hơn, hãy nói rõ bạn cần: giải thích, tóm tắt, so sánh hay hướng dẫn từng bước."
    )


@app.get("/")
def root():
    return {"message": "Firebase chatbot API is running."}


@app.get("/app", include_in_schema=False)
def frontend_app():
    return FileResponse(frontend_dir / "index.html")


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

    recent_messages = load_recent_messages(current_user["uid"])
    reply = generate_reply(user_message, recent_messages)
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
