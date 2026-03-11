import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

import rag_engine  # noqa: F401 – triggers model loading at startup

load_dotenv()

app = FastAPI(title="Mini Notebook – Zalo Bot Webhook")

ZALO_OA_ACCESS_TOKEN = os.getenv("ZALO_OA_ACCESS_TOKEN", "")
ZALO_SEND_MESSAGE_URL = "https://openapi.zalo.me/v3.0/oa/message/cs"

# ThreadPoolExecutor dùng riêng để chạy LlamaIndex query (sync) mà
# không block FastAPI event loop và không gây asyncio conflict
_executor = ThreadPoolExecutor(max_workers=4)

# ─── Helper ──────────────────────────────────────────────────────────────────


def _send_zalo_message_sync(user_id: str, text: str) -> None:
    """Gửi tin nhắn văn bản tới user qua Zalo OA API (sync, chạy trong thread)."""
    if not ZALO_OA_ACCESS_TOKEN:
        print("[Zalo] ZALO_OA_ACCESS_TOKEN chưa được cấu hình – bỏ qua gửi tin nhắn.")
        return

    payload = {
        "recipient": {"user_id": user_id},
        "message": {"text": text},
    }
    headers = {
        "Content-Type": "application/json",
        "access_token": ZALO_OA_ACCESS_TOKEN,
    }
    with httpx.Client(timeout=10.0) as client:
        response = client.post(ZALO_SEND_MESSAGE_URL, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get("error") == 0:
                print(f"[Zalo] Gửi tin nhắn thành công tới user {user_id}.")
            else:
                print(f"[Zalo] Lỗi từ Zalo API: {data}")
        else:
            print(f"[Zalo] HTTP Error {response.status_code}: {response.text}")


async def send_zalo_message(user_id: str, text: str) -> None:
    """Wrapper async — chạy gửi Zalo trong thread để tránh sniffio conflict."""
    await asyncio.to_thread(_send_zalo_message_sync, user_id, text)


# ─── Routes ──────────────────────────────────────────────────────────────────


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "Mini Notebook Zalo Bot"}


@app.post("/webhook")
async def zalo_webhook(request: Request):
    """
    Nhận event từ Zalo OA webhook.

    Zalo gửi HTTP POST với Content-Type: application/json.
    Luôn phải trả về HTTP 200 OK để Zalo không retry.
    """
    try:
        body = await request.json()
    except Exception:
        # Nếu không parse được JSON, vẫn trả 200 để Zalo không retry liên tục
        return JSONResponse(content={"status": "ignored"}, status_code=200)

    print(f"[Webhook] Nhận body: {body}")
    event_name = body.get("event_name", "")
    print(f"[Webhook] Nhận event: {event_name}")

    if event_name == "message.text.received":
        # Lấy thông tin người gửi và nội dung tin nhắn
        sender_id: str = body.get("message", {}).get("from", {}).get("id")
        message_text: str = body.get("message", {}).get("text", "").strip()

        if not sender_id or not message_text:
            print("[Webhook] Thiếu sender_id hoặc message_text, bỏ qua.")
            return JSONResponse(content={"status": "ignored"}, status_code=200)

        print(f"[Webhook] User {sender_id!r} hỏi: {message_text!r}")

        # Chạy sync LlamaIndex query trong thread riêng để tránh asyncio conflict
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(_executor, rag_engine.query, message_text)

        # Gửi câu trả lời về cho user qua Zalo OA API
        await send_zalo_message(sender_id, answer)

    # Với mọi event khác (follow, unfollow, v.v.) → bỏ qua, vẫn trả 200
    return JSONResponse(content={"status": "ok"}, status_code=200)
