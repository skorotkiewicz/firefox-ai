#!/usr/bin/env python3
"""Local chat server using litert_lm with uvicorn + FastAPI + SSL support."""

from __future__ import annotations

import json
import os
import sys
import re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import litert_lm
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = "gemma-4-E2B-it.litertlm"

DEFAULT_SYSTEM_PROMPT = (
    "- You are LLM named Bubby.\n"
    "- Do not attempt to guess or elaborate. Do not speculate or fill in gaps.\n"
    "- Be concise."
)

STOP_SEQUENCES = ["<|end|>", "<|eot_id|>", "</s>"]

engine = None
conversation = None


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def resolve_model_path() -> str:
    path = os.environ.get("MODEL_PATH", "")
    if path:
        return path
    local_model = ROOT / DEFAULT_MODEL
    if local_model.exists():
        return str(local_model)
    from huggingface_hub import hf_hub_download
    repo = os.environ.get("HF_REPO", "litert-community/gemma-4-E2B-it-litert-lm")
    filename = os.environ.get("HF_FILENAME", DEFAULT_MODEL)
    print(f"Downloading {repo}/{filename} (first run only)...")
    return hf_hub_download(repo_id=repo, filename=filename)


def init_engine() -> None:
    global engine
    model_path = resolve_model_path()
    print(f"Loading model from {model_path}...")
    backend_str = os.environ.get("BACKEND", "GPU").upper()
    vision_str = os.environ.get("VISION_BACKEND", "GPU").upper()
    audio_str = os.environ.get("AUDIO_BACKEND", "CPU").upper()
    backend = getattr(litert_lm.Backend, backend_str, litert_lm.Backend.GPU)
    vision_backend = getattr(litert_lm.Backend, vision_str, litert_lm.Backend.GPU)
    audio_backend = getattr(litert_lm.Backend, audio_str, litert_lm.Backend.CPU)
    engine = litert_lm.Engine(
        model_path,
        backend=backend,
        vision_backend=vision_backend,
        audio_backend=audio_backend,
    )
    engine.__enter__()
    print("Engine loaded successfully.")


def cleanup_engine() -> None:
    global engine
    if engine:
        engine.__exit__(None, None, None)
        engine = None


def get_current_time() -> str:
    return datetime.now().astimezone().strftime("%A, %B %d, %Y, %I:%M:%S %p %Z")


def get_system_prompt() -> str:
    base_prompt = os.environ.get("LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
    return f"{base_prompt}\n\nCurrent date and time: {get_current_time()}"


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content")
        if isinstance(content, str):
            text = content
        else:
            parts = message.get("parts", [])
            if isinstance(content, list):
                parts = content
            text_chunks = []
            for part in parts:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_chunks.append(part.get("text", ""))
                    elif "text" in part:
                        text_chunks.append(part["text"])
            text = "".join(text_chunks)
        normalized.append({"role": role, "content": text})
    return normalized


def build_conversation(messages: list[dict[str, Any]]) -> Any:
    global conversation
    if engine is None:
        raise RuntimeError("Engine not initialized")
    normalized = normalize_messages(messages)
    full_messages = [{"role": "system", "content": get_system_prompt()}]
    full_messages.extend(normalized)
    conversation = engine.create_conversation(messages=full_messages)
    conversation.__enter__()
    return conversation


def cleanup_conversation() -> None:
    global conversation
    if conversation:
        conversation.__exit__(None, None, None)
        conversation = None


def generate_stream(conversation: Any, message: dict[str, Any]) -> Generator[str, None, None]:
    try:
        response = conversation.send_message(message)
        if isinstance(response, dict):
            content = response.get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "")
            else:
                text = str(response)
        else:
            text = str(response)
        words = re.findall(r'\S+\s*', text)
        for word in words:
            yield word
    except Exception as e:
        yield f"[Error: {e}]"


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Chat (Local)</title>
  <style>
    :root { color-scheme: dark; --bg: #0a0a0a; --panel: #171717; --panel-2: #262626; --panel-3: #404040; --text: #ededed; --muted: #a3a3a3; --border: #262626; --user: #404040; --assistant: #171717; --accent: #525252; }
    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body { margin: 0; background: var(--bg); color: var(--text); font-family: Arial, Helvetica, sans-serif; }
    .app { height: 100vh; display: flex; flex-direction: column; }
    .header, .composer { display: flex; align-items: center; padding: 12px 16px; border-color: var(--border); background: var(--panel); }
    .header { justify-content: space-between; border-bottom: 1px solid var(--border); }
    .composer { gap: 8px; border-top: 1px solid var(--border); }
    h2 { margin: 0; font-size: 1.125rem; }
    button { border: 0; cursor: pointer; font: inherit; padding: 8px 16px; border-radius: 8px; background: var(--accent); color: #fff; }
    button:disabled { opacity: 0.5; }
    .messages { flex: 1; overflow-y: auto; padding: 16px; }
    .message-row { display: flex; margin-bottom: 16px; }
    .message-row.user { justify-content: flex-end; }
    .bubble { max-width: 80%; border-radius: 12px; padding: 10px 16px; font-size: 0.875rem; line-height: 1.5; }
    .bubble.user { background: var(--user); color: #fff; white-space: pre-wrap; }
    .bubble.assistant { background: var(--assistant); }
    textarea { flex: 1; min-height: 44px; resize: none; padding: 10px; border: 1px solid var(--panel-3); border-radius: 10px; background: var(--panel-2); color: var(--text); }
  </style>
</head>
<body>
  <div class="app">
    <div class="header">
      <h2>Chat (Local)</h2>
      <button id="clearBtn">Clear</button>
    </div>
    <div id="messages" class="messages"></div>
    <form id="chatForm" class="composer">
      <textarea id="input" rows="3" placeholder="Type message..."></textarea>
      <button type="submit" id="sendBtn">Send</button>
    </form>
  </div>
  <script>
    const messages = [];
    const messagesDiv = document.getElementById("messages");
    const input = document.getElementById("input");
    const form = document.getElementById("chatForm");
    function addMessage(role, content) {
      const row = document.createElement("div");
      row.className = `message-row ${role}`;
      const bubble = document.createElement("div");
      bubble.className = `bubble ${role}`;
      bubble.textContent = content;
      row.appendChild(bubble);
      messagesDiv.appendChild(row);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      addMessage("user", text);
      messages.push({ role: "user", content: text });
      input.value = "";
      input.disabled = true;
      const assistantRow = document.createElement("div");
      assistantRow.className = "message-row assistant";
      const assistantBubble = document.createElement("div");
      assistantBubble.className = "bubble assistant";
      assistantRow.appendChild(assistantBubble);
      messagesDiv.appendChild(assistantRow);
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [...messages] }),
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        fullText += decoder.decode(value, { stream: true });
        assistantBubble.textContent = fullText;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
      }
      messages.push({ role: "assistant", content: fullText });
      input.disabled = false;
      input.focus();
    });
    document.getElementById("clearBtn").addEventListener("click", () => {
      messages.length = 0;
      messagesDiv.innerHTML = "";
    });
  </script>
</body>
</html>
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    try:
        init_engine()
        yield
    finally:
        cleanup_engine()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return HTMLResponse(content=INDEX_HTML)


@app.post("/api/chat")
async def chat(request: dict):
    messages = request.get("messages", [])
    
    def stream():
        conv = build_conversation(messages[:-1] if messages else [])
        last_message = messages[-1] if messages else {"role": "user", "content": "Hello"}
        try:
            for chunk in generate_stream(conv, last_message):
                yield chunk.encode("utf-8")
        finally:
            cleanup_conversation()
    
    return StreamingResponse(stream(), media_type="text/plain")


def main():
    port = int(os.environ.get("PORT", "3000"))
    host = os.environ.get("HOST", "0.0.0.0")
    
    ssl_keyfile = os.environ.get("SSL_KEYFILE")
    ssl_certfile = os.environ.get("SSL_CERTFILE")
    
    print(f"Starting server on {host}:{port}")
    if ssl_keyfile and ssl_certfile:
        print(f"SSL enabled: {ssl_certfile}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile,
    )


if __name__ == "__main__":
    main()
