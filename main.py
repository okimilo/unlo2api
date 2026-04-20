from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from curl_cffi import requests
import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

app = FastAPI(title="Clauder - UnlimitedAI 代理 (增强版)")

COOKIE = os.getenv("UNLIMITEDAI_COOKIE")

def enrich_message(msg: Dict[str, Any]) -> Dict[str, Any]:
    """将消息格式化为与官网完全一致的结构"""
    content = msg.get("content", "")
    if isinstance(content, list):
        parts = content
    else:
        parts = [{"type": "text", "text": str(content)}]
    
    return {
        "id": msg.get("id") or str(uuid.uuid4()),
        "role": msg.get("role", "user"),
        "content": content if isinstance(content, str) else "",
        "parts": parts,
        "createdAt": msg.get("createdAt") or datetime.now(timezone.utc).isoformat()
    }

@app.get("/")
async def root():
    return {"status": "ok", "message": "🚀 Clauder (UnlimitedAI 增强代理) 已启动！"}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效 JSON")

    raw_messages: List[Dict] = body.get("messages", [])
    if not raw_messages:
        raise HTTPException(status_code=400, detail="messages 为空")

    # 关键修复：将每条消息格式化为官网完全一致的结构
    enriched_messages = [enrich_message(m) for m in raw_messages]

    # 支持多个模型名：unlimitedai.chat / chat-model-reasoning 等
    incoming_model = body.get("model", "chat-model-reasoning")
    selected_model = incoming_model if incoming_model else "chat-model-reasoning"

    payload = {
        "chatId": str(uuid.uuid4()),
        "messages": enriched_messages,
        "selectedChatModel": selected_model,
        "selectedCharacter": None,
        "selectedStory": None,
        "deviceId": "444ddb4f-064d-4a86-9c92-af697bb6512e",
        "locale": "en"
    }

    headers = {
        "content-type": "application/json",
        "origin": "https://app.unlimitedai.chat",
        "referer": "https://app.unlimitedai.chat/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "cookie": COOKIE
    }

    try:
        resp = requests.post(
            "https://app.unlimitedai.chat/api/chat",
            headers=headers,
            json=payload,
            stream=True,
            impersonate="chrome120",
            timeout=60
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"上游请求失败: {str(e)}")

    if resp.status_code != 200:
        error_text = resp.text[:500] if resp.text else "未知错误"
        raise HTTPException(status_code=502, detail=f"上游返回错误 {resp.status_code}: {error_text}")

    def generate():
        for line in resp.iter_lines():
            if not line:
                continue
            line_str = line.decode('utf-8').strip()
            if line_str.startswith("{"):
                try:
                    data = json.loads(line_str)
                    if data.get("type") == "delta" and data.get("delta"):
                        content = data["delta"]
                        if content:
                            yield f'data: {json.dumps({"choices": [{"delta": {"content": content}}]})}\n\n'
                except:
                    pass
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
