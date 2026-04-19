from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import requests
import json
import os
import uuid
from typing import List, Dict

app = FastAPI(title="UnlimitedAI.Chat Web2API - 完美伪装版")

# 从环境变量读取（推荐在平台设置）
COOKIE = os.getenv("UNLIMITEDAI_COOKIE")  # ← 关键！把你抓到的整个 cookie 字符串放这里

@app.get("/")
async def root():
    return {"status": "ok", "message": "🚀 UnlimitedAI.Chat Web2API 已启动（无限免费版）"}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效 JSON")

    messages: List[Dict] = body.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="messages 为空")

    # 取最后一条用户消息（或完整历史）
    last_user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "你好")

    # 动态生成新 chatId（防止上下文污染）
    chat_id = str(uuid.uuid4())

    payload = {
        "chatId": chat_id,
        "messages": [{"role": "user", "content": last_user_msg, "parts": [{"type": "text", "text": last_user_msg}]}],
        "selectedChatModel": "chat-model-reasoning",   # 可改成其他模型
        "selectedCharacter": None,
        "selectedStory": None,
        "deviceId": "79f760f9-0e37-4b9c-be12-49afab3c6c90",  # 可从你 cookie 里提取
        "locale": "zh"
    }

    headers = {
        "content-type": "application/json",
        "origin": "https://app.unlimitedai.chat",
        "referer": "https://app.unlimitedai.chat/zh",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "accept": "*/*",
        "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "cookie": COOKIE   # ← 这里放你抓到的完整 cookie 字符串
    }

    resp = requests.post("https://app.unlimitedai.chat/api/chat", headers=headers, json=payload, stream=True)

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
