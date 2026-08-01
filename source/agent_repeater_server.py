from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

from main import handle_chat_request


app = FastAPI()


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    status: str
    reply: str
    target_agent: Optional[str] = None


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    # Агенты поднимаются лениво внутри main.get_agents() при первом
    # обращении - и CLI, и репитер работают с одним и тем же набором.
    result = await handle_chat_request(req.session_id, req.message)

    if result["status"] == "clarify":
        return ChatResponse(status="clarify", reply=result["question"])

    if result["status"] == "error":
        return ChatResponse(status="error", reply=result.get("raw", ""))

    return ChatResponse(status="ready", reply=result["reply"], target_agent=result["target_agent"])


def run(lhost: str, lport: int):
    print(f"[*] MAS-сервер запущен на http://{lhost}:{lport}")
    uvicorn.run(app, host=lhost, port=lport)
