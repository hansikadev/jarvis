from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import traceback

from agent import ask_agent, reload_data

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    history: List[Dict[str, Any]] = []


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    try:
        reply = ask_agent(request.message, request.history)
        return ChatResponse(response=reply)
    except Exception as e:
        # Print the full traceback to the terminal running uvicorn so the
        # real error is visible, instead of only a generic message reaching
        # the frontend.
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reload")
def reload_endpoint():
    """Reload the Excel data without restarting the server (call this after editing pod4jsr.xlsx)."""
    try:
        reload_data()
        return {"message": "Data reloaded successfully."}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def read_root():
    return {"message": "Jarvis Backend is running!"}
