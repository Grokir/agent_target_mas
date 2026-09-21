"""
Конвертер (shim) между Координатором и LM Studio для db_agent.

Идея:
  - Координатор шлёт обычный OpenAI-совместимый запрос с полем "tools".
  - Конвертер УБИРАЕТ "tools" перед пересылкой в LM Studio -> модель работает
    в чистом текстовом режиме (никакого peg-native / grammar detection),
    инструменты уже описаны текстом в системном промпте (документ 1).
  - Сырой текстовый ответ модели парсится и, если это вызов инструмента,
    упаковывается обратно в стандартный OpenAI "tool_calls" формат.
  - Координатор получает ответ, неотличимый от "настоящего" native tool-calling.

Запуск:
  pip install fastapi uvicorn httpx
  uvicorn tool_call_converter:app --port 8000

Координатор нужно перенаправить на этот адрес (http://localhost:8000/v1/chat/completions)
вместо прямого обращения к LM Studio (http://localhost:1234/v1/chat/completions).
"""

import json
import re
import time
import uuid

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# LM_STUDIO_BACKEND = "http://localhost:1234/v1/chat/completions"
# LM_STUDIO_BACKEND = "http://localhost:1234/v1"
# LM_STUDIO_BACKEND = "http://192.168.0.105:5002"
LM_STUDIO_BACKEND = "http://192.168.0.105:5002/v1/chat/completions"



# --- Парсинг сырого текста модели в наш внутренний формат ---
def extract_tool_call(raw_text: str) -> dict | None:
    if not raw_text:
        return None

    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE)

    start = cleaned.find("{")
    if start == -1:
        return None

    depth = 0
    end = None
    for i, ch in enumerate(cleaned[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return None

    candidate = cleaned[start:end]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict) or "tool" not in data or "arguments" not in data:
        return None
    return data


# --- Упаковка в стандартный OpenAI tool_calls формат ---
def to_openai_tool_calls(parsed: dict) -> list[dict]:
    return [{
        "id": f"call_{uuid.uuid4().hex[:24]}",
        "type": "function",
        "function": {
            "name": parsed["tool"],
            # По спецификации OpenAI это JSON-СТРОКА, а не объект
            "arguments": json.dumps(parsed["arguments"], ensure_ascii=False),
        },
    }]


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()

    # Запоминаем, просил ли клиент tools вообще (иначе не пытаемся парсить как tool-call)
    tools_requested = bool(body.get("tools"))

    # Убираем поле "tools" перед пересылкой -> LM Studio не включает grammar/peg-native
    forward_body = dict(body)
    forward_body.pop("tools", None)
    forward_body.pop("tool_choice", None)

    async with httpx.AsyncClient(timeout=300) as client:
        backend_resp = await client.post(LM_STUDIO_BACKEND, json=forward_body)
    backend_resp.raise_for_status()
    data = backend_resp.json()

    message = data["choices"][0]["message"]
    raw_content = message.get("content", "")

    parsed = extract_tool_call(raw_content) if tools_requested else None

    if parsed is not None:
        message["content"] = None
        message["tool_calls"] = to_openai_tool_calls(parsed)
        data["choices"][0]["finish_reason"] = "tool_calls"
    # иначе оставляем content как есть — это обычный текстовый ответ

    return JSONResponse(data)
