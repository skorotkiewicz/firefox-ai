# Firefox AI Sidebar

A minimal AI chat interface for Firefox sidebar. Clean, fast, and history-free.

## Setup

```bash
cp .env.example .env
# Edit .env with your LLM endpoint
bun dev
# or just
python3 server.py
```

## Configure

Edit `.env`:

```env
LLM_BASE_URL=https://api.example.com/v1
LLM_API_KEY=your-key
LLM_MODEL=kimi
LLM_SYSTEM_PROMPT=You are a helpful assistant.
```

## Firefox Sidebar Setup

1. Navigate to `about:config` in Firefox
2. Search for `browser.ml.chat.hideLocalhost` and set to **false**
3. Set `browser.ml.chat.provider` to your URL (e.g., `http://localhost:5173`)
4. Open Firefox AI chat sidebar – your local endpoint appears in the dropdown

## Cool model for having fun
https://huggingface.co/mradermacher/gemma-4-E2B-it-heretic-ara-GGUF
