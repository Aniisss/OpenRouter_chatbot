from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from collections import deque
import aiohttp
import os

# Load the API key from an environment variable
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set in environment variables.")

# Request schema
class ChatRequest(BaseModel):
    message: str

# Response schema
class ChatResponse(BaseModel):
    response: str

# Chat handler class
class OpenRouterChatApp:
    def __init__(self):
        self.session = None
        self.selected_model = "openai/gpt-3.5-turbo"  # Default model
        self.conversation_history = deque(maxlen=30)
        self.semaphore = asyncio.Semaphore(10)

    async def init_session(self):
        self.session = aiohttp.ClientSession()

    async def close_session(self):
        if self.session:
            await self.session.close()

    async def get_chat_completion(self, user_input):
        async with self.semaphore:
            self.add_to_conversation_history("user", user_input)
            api_url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://yourdomain.com",
                "X-Title": "OpenRouter FastAPI Chat",
            }
            data = {
                "model": self.selected_model,
                "messages": list(self.conversation_history)
            }

            async with self.session.post(url=api_url, headers=headers, json=data) as response:
                if response.status != 200:
                    raise HTTPException(status_code=response.status, detail=await response.text())
                api_result = await response.json()
                reply = api_result.get("choices")[0].get("message")
                return reply.get("content")

    def add_to_conversation_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})

# FastAPI app setup
app = FastAPI()
chat_app = OpenRouterChatApp()

@app.on_event("startup")
async def on_startup():
    await chat_app.init_session()

@app.on_event("shutdown")
async def on_shutdown():
    await chat_app.close_session()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    reply = await chat_app.get_chat_completion(request.message)
    return ChatResponse(response=reply)
