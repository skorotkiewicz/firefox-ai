#!/usr/bin/env python3
"""Local chat server using litert_lm."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator

import litert_lm
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = "gemma-4-E2B-it.litertlm"

DEFAULT_SYSTEM_PROMPT = (
    "- You are LLM named Bubby.\n"
    "- Do not attempt to guess or elaborate. Do not speculate or fill in gaps.\n"
    "- Be concise.\n"
    "- You can see images and hear audio that the user shares with you."
)


def save_temp_file(data: bytes, suffix: str) -> str:
    """Save bytes to a temporary file and return the path."""
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(data)
    tmp.close()
    return tmp.name


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


def generate_stream(
    conversation: Any, message: dict[str, Any]
) -> Generator[str, None, None]:
    """Generate true streaming response from the model using send_message_async."""
    try:
        # Use send_message_async for true token-by-token streaming
        for chunk in conversation.send_message_async(message):
            if isinstance(chunk, dict):
                content = chunk.get("content", [])
                if content and isinstance(content, list):
                    for item in content:
                        if item.get("type") == "text":
                            text = item.get("text", "")
                            if text:
                                yield text
            elif isinstance(chunk, str):
                yield chunk
    except Exception as e:
        yield f"[Error: {e}]"


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    try:
        init_engine()
        yield
    finally:
        cleanup_engine()


app = FastAPI(lifespan=lifespan)

# app.mount("/static", StaticFiles(directory=str(ROOT)), name="static")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return HTMLResponse(content=(ROOT / "index.html").read_text())


@app.post("/api/chat")
async def chat(
    messages: str = Form(...),
    audio: UploadFile | None = File(None),
    image: UploadFile | None = File(None),
):
    """Chat endpoint supporting text, audio, and image inputs."""
    messages_list = json.loads(messages)

    # Save uploaded files to temp
    audio_path = None
    image_path = None

    try:
        if audio:
            audio_data = await audio.read()
            audio_path = save_temp_file(audio_data, ".wav")
        if image:
            image_data = await image.read()
            image_path = save_temp_file(image_data, ".jpg")

        def stream():
            conv = build_conversation(messages_list[:-1] if messages_list else [])

            # Build multimodal content
            content = []
            if audio_path:
                content.append({"type": "audio", "path": os.path.abspath(audio_path)})
            if image_path:
                content.append({"type": "image", "path": os.path.abspath(image_path)})

            # Add text prompt based on what's present
            if audio_path and image_path:
                content.append(
                    {
                        "type": "text",
                        "text": "The user shared audio and an image. Respond to what they said and describe what you see.",
                    }
                )
            elif audio_path:
                content.append(
                    {
                        "type": "text",
                        "text": "The user shared audio. Respond to what they said.",
                    }
                )
            elif image_path:
                content.append(
                    {
                        "type": "text",
                        "text": "The user shared an image. Describe what you see.",
                    }
                )
            else:
                # No files, use last message text
                last_msg = (
                    messages_list[-1]
                    if messages_list
                    else {"role": "user", "content": "Hello"}
                )
                content = last_msg.get("content", "Hello")

            last_message = {"role": "user", "content": content}

            try:
                for chunk in generate_stream(conv, last_message):
                    yield chunk.encode("utf-8")
            finally:
                cleanup_conversation()
                # Cleanup temp files
                for p in [audio_path, image_path]:
                    if p and os.path.exists(p):
                        os.unlink(p)

        return StreamingResponse(stream(), media_type="text/plain")
    except Exception as e:
        # Cleanup on error
        for p in [audio_path, image_path]:
            if p and os.path.exists(p):
                os.unlink(p)
        raise


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
    load_dotenv()
    main()
