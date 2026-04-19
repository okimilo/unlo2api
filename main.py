from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from curl_cffi import requests  # 关键：换成伪装库
import json
import os
import uuid
from typing import List, Dict

app = FastAPI(title="UnlimitedAI.Chat Web2API - 究极伪装版")

COOKIE = os.getenv("UNLIMITEDAI_COOKIE") 

@app.get("/")
async def root():
    return {"status": "ok", "message": "🚀 UnlimitedAI Web2API 究极伪装版已启动！"}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效 JSON")

    messages: List[Dict] = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages 为空")

    last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "你好")
    chat_id = str(uuid.uuid4())

    payload = {
        "chatId": chat_id,
        "messages": [{"role": "user", "content": last_user_msg, "parts": [{"type": "text", "text": last_user_msg}]}],
        "selectedChatModel": body.get("model", "chat-model-reasoning"),
        "selectedCharacter": None,
        "selectedStory": None,
        "deviceId": "79f760f9-0e37-4b9c-be12-49afab3c6c90", 
        "locale": "zh"
    }

    headers = {
        "content-type": "application/json",
        "origin": "https://app.unlimitedai.chat",
        "referer": "https://app.unlimitedai.chat/zh",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "cookie": COOKIE
    }

    # 关键：impersonate 完美模拟浏览器底层指纹
    resp = requests.post("https://app.unlimitedai.chat/api/chat", headers=headers, json=payload, stream=True, impersonate="chrome120")

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
