from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from main import handle_chat_request


WEB_INDEX = Path(__file__).resolve().parent / "index.html"


app = FastAPI()

# Репитер - внешний HTTP-интерфейс MAS (роль "сервера", как у ollama serve),
# клиенты (web/index.html и другие) живут на других origin - разрешаем всем.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    status: str
    reply: str
    target_agent: Optional[str] = None


@app.get("/")
async def index():
    return FileResponse(WEB_INDEX)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MAS repeater"}


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
