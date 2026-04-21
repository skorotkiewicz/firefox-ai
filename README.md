# Local Chat Server (LiteRT-LM)

A local chat server using Google's Gemma-4 model via LiteRT-LM with real token streaming, tool support, and multimodal capabilities.

## Features

- **Real streaming** - Token-by-token streaming via `send_message_async()`
- **Tool support** - Web search, URL fetch, and weather lookup
- **Multimodal** - Text, image, and audio input with user text preservation
- **Web UI** - Clean interface with theme-aware markdown rendering
- **Firefox sidebar** - URL parameter support (`?q=`) for instant queries
- **Local AI** - Runs entirely on your machine (GPU recommended)

## Quick Start

```bash
# Install dependencies
uv sync

# Run the server
uv run server.py
```

Server starts at `http://localhost:3000`

## Model

First run will download the model (~4GB) from HuggingFace:
- Repo: `litert-community/gemma-4-E2B-it-litert-lm`
- File: `gemma-4-E2B-it.litertlm`

Or place the model file in the project directory.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | 3000 | Server port |
| `HOST` | 0.0.0.0 | Bind address |
| `BACKEND` | GPU | Compute backend (GPU/CPU) |
| `VISION_BACKEND` | GPU | Vision backend |
| `AUDIO_BACKEND` | CPU | Audio backend |
| `MODEL_PATH` | - | Custom model path |

## API

### GET /api/health

Health check endpoint.

**Response:** `{"status": "ok", "engine_loaded": true/false}`

### POST /api/chat

Chat endpoint with NDJSON streaming response.

**Form data:**
- `messages` (string) - JSON array of message objects
- `audio` (file, optional) - Audio file
- `image` (file, optional) - Image file

**Response:** `application/x-ndjson` streaming events

**Event types:**
- `{"type": "text", "text": "..."}` - Token stream
- `{"type": "tool_use", "name": "..."}` - Tool execution indicator
- `{"type": "error", "text": "..."}` - Error message

## Architecture

### Streaming
Uses `send_message_async()` with a thread-safe queue to stream real tokens from the model to the client via NDJSON.

### Tools
Three tools available via `ToolEventHandler`:
- `web_search(query, num_results=8)` - Search DuckDuckGo and return results
- `web_fetch(url, format="markdown")` - Fetch URL content in markdown/text/html
- `get_weather(location)` - Get weather from wttr.in
<!--- `web_browser(url)` - Fetch and extract webpage text-->

### Multimodal
Supports images and audio while **preserving the user's actual text message**:
```python
content = [
    {"type": "image", "path": "/path/to/image.jpg"},
    {"type": "audio", "path": "/path/to/audio.wav"},
    {"type": "text", "text": "What's in this picture and what did they say?"}
]
```

## Project Structure

```
server-litert/
├── server.py          # FastAPI server with streaming
├── tool/              # LLM-callable tools
│   ├── __init__.py    # Tool exports
│   ├── _utils.py      # Shared utilities (URL sanitization)
│   ├── web_search.py  # DuckDuckGo search
│   ├── web_fetch.py   # URL content fetcher
│   ├── get_weather.py # Weather lookup
│   └── web_browser.py # Available but disabled
├── index.html         # Web UI with Firefox sidebar support
├── static/
│   └── style.css      # Theme-aware styles
└── pyproject.toml     # Dependencies
```

## License

MIT
