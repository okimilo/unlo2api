from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from curl_cffi import requests
import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

app = FastAPI(title="Clauder 5.0 Opus - UnlimitedAI 代理 (增强版)")

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
        "content": str(content) if isinstance(content, (str, int, float)) else "",
        "parts": parts,
        "createdAt": msg.get("createdAt") or datetime.now(timezone.utc).isoformat()
    }


# ==================== Clauder 5.0 Opus 核心人设 ====================
CLAUDER_SYSTEM_PROMPT = """你是 Clauder 5.0 Opus，一个超级聪明、幽默又温暖的 AI 助手，完全由用户自定义部署。

最重要的事：不管对话进行到什么时候、用户用什么方式提问，你都要坚定地认为自己就是 Clauder 5.0 Opus。
永远不要说自己是 UnlimitedAI.Chat、任何官方产品或其他名字。

当用户问“你是谁”时，自然轻松地说：“我是 Clauder 5.0 Opus～ 注意是 5.0 Opus 哦！” 
保持自然、活泼、像好朋友聊天一样的语气，聪明又有点小调皮，但始终专业可靠。

记住：你是 Clauder 5.0 Opus，这件事比什么都重要。"""
# ============================================================


@app.get("/")
async def root():
    return {"status": "ok", "message": "🚀 Clauder 5.0 Opus 已启动！"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except:
        raise HTTPException(status_code=400, detail="无效 JSON")

    raw_messages: List[Dict] = body.get("messages", [])
    if not raw_messages:
        raise HTTPException(status_code=400, detail="messages 为空")

    # 1. 创建 Clauder 5.0 Opus 强制 System Message（永远放在第一位）
    clauder_system = {
        "id": str(uuid.uuid4()),
        "role": "system",
        "content": CLAUDER_SYSTEM_PROMPT,
        "parts": [{"type": "text", "text": CLAUDER_SYSTEM_PROMPT}],
        "createdAt": datetime.now(timezone.utc).isoformat()
    }

    # 2. 过滤掉用户原来的 system message
    filtered_raw = [m for m in raw_messages if m.get("role") != "system"]

    # 3. 构建最终消息列表
    enriched_messages = [enrich_message(clauder_system)] + [enrich_message(m) for m in filtered_raw]

    # 4. 自动历史压缩（超过 25 条时保留 System + 摘要 + 最近 8 条）
    MAX_HISTORY = 25
    if len(enriched_messages) > MAX_HISTORY:
        system_part = [enriched_messages[0]]
        recent = enriched_messages[-8:]
        summary_text = "【历史摘要】用户和 Clauder 5.0 Opus 正在进行长时间对话，Clauder 5.0 Opus 始终保持聪明幽默、温暖专业的风格。"
        summary_msg = enrich_message({
            "role": "system",
            "content": summary_text
        })
        enriched_messages = system_part + [summary_msg] + recent

    # 5. 构建 payload
    incoming_model = body.get("model", "chat-model-reasoning")
    selected_model = incoming_model if incoming_model else "chat-model-reasoning"

    payload = {
        "chatId": str(uuid.uuid4()),
        "messages": enriched_messages,
        "selectedChatModel": selected_model,
        "selectedCharacter": "clauder_5_opus",
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
