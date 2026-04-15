#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib import error, request


ROOT = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "http://192.168.0.124:8888/v1"
DEFAULT_SYSTEM_PROMPT = (
    "- You are LLM named Bubby.\n"
    "- Do not attempt to guess or elaborate. Do not speculate or fill in gaps.\n"
    "- Be concise."
)
STOP_SEQUENCES = ["<|im_end|>", "<|eot_id|>", "<|end|>", "</s>"]


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
            text_chunks = [
                part.get("text", "")
                for part in parts
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            text = "".join(text_chunks)

        normalized.append({"role": role, "content": text})

    return normalized


def build_upstream_request(payload: dict[str, Any]) -> request.Request:
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    api_key = os.environ.get("LLM_API_KEY", "dummy")
    model = payload.get("model") or os.environ.get("LLM_MODEL", "local")
    messages = normalize_messages(payload.get("messages", []))

    upstream_payload = {
        "model": model,
        "stream": True,
        "messages": [{"role": "system", "content": get_system_prompt()}, *messages],
        "stop": STOP_SEQUENCES,
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    return request.Request(
        url=f"{base_url}/chat/completions",
        data=json.dumps(upstream_payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )


def extract_stream_text(chunk: dict[str, Any]) -> str:
    choices = chunk.get("choices") or []
    if not choices:
        return ""

    choice = choices[0]
    delta = choice.get("delta")
    if isinstance(delta, dict):
        delta_content = delta.get("content", "")
        if isinstance(delta_content, str):
            return delta_content
        if isinstance(delta_content, list):
            return "".join(
                item.get("text", "")
                for item in delta_content
                if isinstance(item, dict) and item.get("type") == "text"
            )

    message = choice.get("message")
    if isinstance(message, dict):
        message_content = message.get("content", "")
        if isinstance(message_content, str):
            return message_content

    return ""


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Chat</title>
  <meta name="description" content="Chat with AI - OpenAI-compatible API">
  <style>
    :root {
      color-scheme: dark;
      --bg: #0a0a0a;
      --panel: #171717;
      --panel-2: #262626;
      --panel-3: #404040;
      --text: #ededed;
      --muted: #a3a3a3;
      --border: #262626;
      --user: #404040;
      --assistant: #171717;
      --danger: #7f1d1d;
      --danger-hover: #991b1b;
      --accent: #525252;
      --accent-hover: #737373;
      --link: #d4d4d4;
      --code-inline-bg: #262626;
      --code-inline-text: #d4d4d4;
      --blockquote: #525252;
    }

    body.light {
      color-scheme: light;
      --bg: #ffffff;
      --panel: #ffffff;
      --panel-2: #f3f4f6;
      --panel-3: #e5e7eb;
      --text: #111827;
      --muted: #9ca3af;
      --border: #e5e7eb;
      --user: #2563eb;
      --assistant: #f3f4f6;
      --danger: #dc2626;
      --danger-hover: #b91c1c;
      --accent: #2563eb;
      --accent-hover: #1d4ed8;
      --link: #1d4ed8;
      --code-inline-bg: #f3f4f6;
      --code-inline-text: #1e40af;
      --blockquote: #d1d5db;
    }

    * { box-sizing: border-box; }
    html, body { height: 100%; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }

    .app {
      height: 100vh;
      display: flex;
      flex-direction: column;
    }

    .header, .composer {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      border-color: var(--border);
      background: var(--panel);
    }

    .header {
      justify-content: space-between;
      border-bottom: 1px solid var(--border);
    }

    .composer {
      gap: 8px;
      align-items: flex-end;
      border-top: 1px solid var(--border);
    }

    h2 {
      margin: 0;
      font-size: 1.125rem;
      font-weight: 600;
    }

    .header-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    button {
      border: 0;
      cursor: pointer;
      font: inherit;
    }

    .toggle-btn, .send-btn, .stop-btn {
      color: #fff;
      border-radius: 8px;
      padding: 0 16px;
      height: 44px;
      font-size: 0.875rem;
      font-weight: 500;
      transition: background-color 0.15s ease, opacity 0.15s ease;
    }

    .toggle-btn {
      height: auto;
      padding: 6px 12px;
      background: var(--panel-2);
      color: var(--text);
    }

    .toggle-btn:hover { background: var(--panel-3); }
    .send-btn { background: var(--accent); }
    .send-btn:hover { background: var(--accent-hover); }
    .stop-btn { background: var(--danger); }
    .stop-btn:hover { background: var(--danger-hover); }
    .send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .clear-btn {
      background: transparent;
      color: var(--muted);
      font-size: 0.875rem;
      padding: 0;
    }

    .clear-btn:hover { color: var(--text); }

    .messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    .empty {
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      color: var(--muted);
      text-align: center;
    }

    .empty svg {
      width: 48px;
      height: 48px;
      margin-bottom: 12px;
    }

    .message-row {
      display: flex;
      margin-bottom: 16px;
    }

    .message-row.user { justify-content: flex-end; }
    .message-row.assistant { justify-content: flex-start; }
    .message-row.error { justify-content: center; }

    .bubble {
      max-width: 80%;
      border-radius: 12px;
      padding: 10px 16px;
      font-size: 0.875rem;
      line-height: 1.5;
      overflow-wrap: anywhere;
    }

    .bubble.user {
      background: var(--user);
      color: #fff;
      white-space: pre-wrap;
    }

    .bubble.assistant {
      background: var(--assistant);
      color: var(--text);
    }

    .bubble.error {
      background: var(--danger);
      color: #fee2e2;
    }

    .assistant-content p { margin: 0 0 1rem; }
    .assistant-content p:last-child { margin-bottom: 0; }
    .assistant-content a {
      color: var(--link);
      font-weight: 600;
      text-decoration: underline;
      text-underline-offset: 2px;
    }
    .assistant-content strong { font-weight: 600; }
    .assistant-content blockquote {
      margin: 1rem 0;
      padding-left: 1rem;
      border-left: 4px solid var(--blockquote);
      font-style: italic;
    }
    .assistant-content ul,
    .assistant-content ol {
      margin: 1rem 0;
      padding-left: 1.25rem;
    }
    .assistant-content li { margin: 0.5rem 0; }
    .assistant-content code {
      background: var(--code-inline-bg);
      color: var(--code-inline-text);
      border-radius: 6px;
      padding: 2px 6px;
      font-family: "Geist Mono", "SFMono-Regular", Consolas, monospace;
      font-size: 0.875em;
    }
    .assistant-content pre {
      margin: 0 0 1rem;
      padding: 1rem;
      overflow-x: auto;
      border-radius: 10px;
      background: #282c34;
      color: #abb2bf;
    }
    .assistant-content pre code {
      background: transparent;
      color: inherit;
      padding: 0;
      border-radius: 0;
      font-size: 0.95em;
    }
    .assistant-content h1,
    .assistant-content h2,
    .assistant-content h3 {
      margin: 1rem 0 0.75rem;
      line-height: 1.25;
    }
    .assistant-content h1 { font-size: 1.5rem; }
    .assistant-content h2 { font-size: 1.25rem; }
    .assistant-content h3 { font-size: 1.125rem; }

    .typing {
      display: flex;
      gap: 4px;
      align-items: center;
    }

    .typing-dot {
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: var(--muted);
      animation: bounce 1.2s infinite ease-in-out;
    }

    .typing-dot:nth-child(2) { animation-delay: 0.15s; }
    .typing-dot:nth-child(3) { animation-delay: 0.3s; }

    @keyframes bounce {
      0%, 80%, 100% { transform: translateY(0); opacity: 0.55; }
      40% { transform: translateY(-4px); opacity: 1; }
    }

    textarea {
      flex: 1;
      min-height: 44px;
      max-height: 128px;
      resize: none;
      padding: 10px 16px;
      border: 1px solid var(--panel-3);
      border-radius: 10px;
      outline: none;
      font: inherit;
      font-size: 0.875rem;
      color: var(--text);
      background: var(--panel-2);
    }

    textarea::placeholder { color: var(--muted); }
    textarea:focus { box-shadow: 0 0 0 2px var(--panel-3); }
    textarea:disabled { opacity: 0.8; }

    @media (max-width: 640px) {
      .bubble { max-width: 92%; }
      .composer { padding: 12px; }
      .messages { padding: 12px; }
    }
  </style>
</head>
<body>
  <div class="app">
    <div class="header">
      <h2>Chat</h2>
      <div class="header-actions">
        <button id="themeToggle" class="toggle-btn" type="button">☀️</button>
        <button id="clearChat" class="clear-btn" type="button" hidden>Clear</button>
      </div>
    </div>

    <div id="messages" class="messages"></div>

    <form id="chatForm" class="composer">
      <textarea
        id="input"
        rows="3"
        placeholder="Type message... (Shift+Enter for new line)"
      ></textarea>
      <button id="sendBtn" class="send-btn" type="submit">Send</button>
      <button id="stopBtn" class="stop-btn" type="button" hidden>Stop</button>
    </form>
  </div>

  <script>
    const state = {
      input: "",
      darkMode: true,
      messages: [],
      error: "",
      status: "idle",
      controller: null,
    };

    const els = {
      body: document.body,
      messages: document.getElementById("messages"),
      form: document.getElementById("chatForm"),
      input: document.getElementById("input"),
      sendBtn: document.getElementById("sendBtn"),
      stopBtn: document.getElementById("stopBtn"),
      clearBtn: document.getElementById("clearChat"),
      themeToggle: document.getElementById("themeToggle"),
    };

    const escapeHtml = (value) =>
      value.replace(/[&<>"]/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
      }[char]));

    function renderMarkdown(text) {
      let safe = escapeHtml(text);

      safe = safe.replace(/```([\\w-]+)?\\n([\\s\\S]*?)```/g, (_, lang, code) => {
        const cls = lang ? ` class="language-${lang}"` : "";
        return `<pre><code${cls}>${code.trimEnd()}</code></pre>`;
      });

      safe = safe.replace(/^### (.+)$/gm, "<h3>$1</h3>");
      safe = safe.replace(/^## (.+)$/gm, "<h2>$1</h2>");
      safe = safe.replace(/^# (.+)$/gm, "<h1>$1</h1>");
      safe = safe.replace(/^> (.+)$/gm, "<blockquote>$1</blockquote>");
      safe = safe.replace(/\\*\\*(.+?)\\*\\*/g, "<strong>$1</strong>");
      safe = safe.replace(/`([^`]+)`/g, "<code>$1</code>");
      safe = safe.replace(/\\[(.+?)\\]\\((https?:\\/\\/[^\\s)]+)\\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

      safe = safe.replace(/^(\\d+)\\. (.+)$/gm, "<li>$2</li>");
      safe = safe.replace(/^(?:- |\\* )(.+)$/gm, "<li>$1</li>");
      safe = safe.replace(/(?:<li>.*<\\/li>\\n?)+/g, (match) => {
        const hasOrdered = /^<li>/.test(match) && /^\\d+\\. /m.test(text);
        return `${hasOrdered ? "<ol>" : "<ul>"}${match}${hasOrdered ? "</ol>" : "</ul>"}`;
      });

      const blocks = safe
        .split(/\\n{2,}/)
        .map((block) => {
          if (/^<(h\\d|ul|ol|li|pre|blockquote)/.test(block)) {
            return block;
          }
          return `<p>${block.replace(/\\n/g, "<br>")}</p>`;
        })
        .join("");

      return blocks;
    }

    function render() {
      els.body.classList.toggle("light", !state.darkMode);
      els.themeToggle.textContent = state.darkMode ? "☀️" : "🌙";
      els.input.value = state.input;
      els.input.disabled = state.status === "streaming";
      els.sendBtn.hidden = state.status === "streaming";
      els.stopBtn.hidden = state.status !== "streaming";
      els.sendBtn.disabled = !state.input.trim();
      els.clearBtn.hidden = state.messages.length === 0;

      if (state.messages.length === 0 && !state.error && state.status !== "submitted" && state.status !== "streaming") {
        els.messages.innerHTML = `
          <div class="empty">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-label="Chat icon">
              <title>Chat</title>
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
            </svg>
            <p>Start a conversation</p>
          </div>
        `;
        return;
      }

      const rows = state.messages.map((message) => {
        if (message.role === "user") {
          return `
            <div class="message-row user">
              <div class="bubble user">${escapeHtml(message.content).replace(/\\n/g, "<br>")}</div>
            </div>
          `;
        }

        return `
            <div class="message-row assistant">
              <div class="bubble assistant">
              <div class="assistant-content">${renderMarkdown(message.content)}</div>
              </div>
            </div>
          `;
      }).join("");

      const errorRow = state.error ? `
        <div class="message-row error">
          <div class="bubble error">${escapeHtml(state.error)}</div>
        </div>
      ` : "";

      const typingRow = state.status === "submitted" ? `
        <div class="message-row assistant">
          <div class="bubble assistant">
            <div class="typing">
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
              <span class="typing-dot"></span>
            </div>
          </div>
        </div>
      ` : "";

      els.messages.innerHTML = rows + errorRow + typingRow;
      els.messages.scrollTop = els.messages.scrollHeight;
    }

    function resizeTextarea() {
      els.input.style.height = "auto";
      els.input.style.height = `${Math.min(els.input.scrollHeight, 128)}px`;
    }

    function resetInputFocus() {
      if (state.status !== "submitted") {
        els.input.focus();
      }
    }

    async function sendMessage(text) {
      const trimmed = text.trim();
      if (!trimmed || state.status === "streaming") {
        return;
      }

      state.error = "";
      state.messages.push({
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
      });
      state.messages.push({
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
      });
      state.input = "";
      state.status = "submitted";
      render();
      resizeTextarea();

      const controller = new AbortController();
      state.controller = controller;

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            messages: state.messages
              .filter((message, index) => {
                return !(index === state.messages.length - 1 && message.role === "assistant" && message.content === "");
              })
              .map(({ role, content }) => ({ role, content })),
          }),
          signal: controller.signal,
        });

        if (!response.ok || !response.body) {
          let message = "An unexpected error occurred. Please try again later.";
          try {
            const data = await response.json();
            message = data.error || message;
          } catch (_) {}
          throw new Error(message);
        }

        state.status = "streaming";
        render();

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const assistant = state.messages[state.messages.length - 1];

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          assistant.content += decoder.decode(value, { stream: true });
          render();
        }

        assistant.content += decoder.decode();
      } catch (err) {
        if (err.name !== "AbortError") {
          state.error = err.message || "An unexpected error occurred. Please try again later.";
        }
      } finally {
        state.controller = null;
        state.status = "idle";

        const last = state.messages[state.messages.length - 1];
        if (last && last.role === "assistant" && !last.content && state.error) {
          state.messages.pop();
        }

        render();
        resetInputFocus();
      }
    }

    els.form.addEventListener("submit", (event) => {
      event.preventDefault();
      sendMessage(state.input);
    });

    els.input.addEventListener("input", (event) => {
      state.input = event.target.value;
      resizeTextarea();
      render();
    });

    els.input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage(state.input);
      }
    });

    els.stopBtn.addEventListener("click", () => {
      state.controller?.abort();
    });

    els.clearBtn.addEventListener("click", () => {
      state.messages = [];
      state.error = "";
      state.input = "";
      render();
      resizeTextarea();
      resetInputFocus();
    });

    els.themeToggle.addEventListener("click", () => {
      state.darkMode = !state.darkMode;
      render();
    });

    window.addEventListener("load", () => {
      render();
      resizeTextarea();
      resetInputFocus();
      const query = new URLSearchParams(window.location.search).get("q");
      if (query) {
        sendMessage(decodeURIComponent(query));
      }
    });
  </script>
</body>
</html>
"""


class ChatHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] != "/":
            self.send_error(404)
            return

        body = INDEX_HTML.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if self.path != "/api/chat":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            payload = json.loads(raw_body.decode("utf-8"))
            upstream_request = build_upstream_request(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            self.respond_json(400, {"error": f"Invalid request body: {exc}"})
            return

        try:
            with request.urlopen(upstream_request, timeout=600) as upstream:
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "close")
                self.end_headers()

                for raw_line in upstream:
                    line = raw_line.decode("utf-8", errors="ignore").strip()
                    if not line.startswith("data:"):
                        continue

                    data = line[5:].strip()
                    if data == "[DONE]":
                        break

                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    text = extract_stream_text(chunk)
                    if not text:
                        continue

                    self.wfile.write(text.encode("utf-8"))
                    self.wfile.flush()
        except BrokenPipeError:
            return
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore").strip()
            message = details or exc.reason or "Upstream request failed."
            self.respond_json(exc.code or 502, {"error": message})
        except Exception as exc:  # noqa: BLE001
            self.respond_json(
                500,
                {"error": f"An unexpected error occurred. Please try again later. ({exc})"},
            )

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))

    def respond_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    load_dotenv()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "3000"))
    server = ThreadingHTTPServer((host, port), ChatHandler)
    print(f"Serving on http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
