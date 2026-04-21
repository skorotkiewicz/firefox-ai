# Local Chat Server (LiteRT-LM)

A local chat server using Google's Gemma-4 model via LiteRT-LM with real token streaming, tool support, and multimodal capabilities.

## Features

- **Real streaming** - Token-by-token streaming via `send_message_async()`
- **Tool support** - Web browser, weather, and search tools
- **Multimodal** - Text, image, and audio input
- **Web UI** - Clean interface with markdown rendering
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
- `web_browser(url)` - Fetch and extract webpage text
- `get_weather(location)` - Get weather from wttr.in
- `web_search(query)` - Search DuckDuckGo and return results

### Multimodal
Supports images and audio by including them in the message content array:
```python
content = [
    {"type": "image", "path": "/path/to/image.jpg"},
    {"type": "audio", "path": "/path/to/audio.wav"},
    {"type": "text", "text": "Describe this"}
]
```

## Project Structure

```
server-litert/
├── server.py          # FastAPI server
├── index.html         # Web UI
├── static/
│   └── style.css      # Styles
└── pyproject.toml     # Dependencies
```

## License

MIT
