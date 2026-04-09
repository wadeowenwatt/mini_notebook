# Mini Notebook — Discord RAG Bot

A **Google Notebook-inspired** chatbot that lets you ask questions about your PDF documents directly in Discord (or Telegram).

Drop PDFs into `data/` → the system embeds them into ChromaDB → ask questions in Discord → the bot retrieves semantically relevant chunks and answers with Google Gemini.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Bot interface** | discord.py 2.3 / python-telegram-bot |
| **RAG framework** | LlamaIndex Core 0.14 |
| **LLM** | Google Gemini 2.5 Flash (`llama-index-llms-google-genai`) |
| **Embedding model** | `BAAI/bge-m3` via HuggingFace — 1024-dim dense vectors, runs locally on CPU/GPU |
| **Vector database** | ChromaDB (separate Docker service, persistent named volume) |
| **Config** | python-dotenv (`.env` file) |
| **Runtime** | Python 3.11, Docker Compose |

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Host Machine                            │
│                                                                 │
│  ┌─────────────────────────── Docker network: rag_net ───────┐  │
│  │                                                           │  │
│  │   ┌──────────────────────┐      ┌─────────────────────┐  │  │
│  │   │     bot container    │      │   chroma container  │  │  │
│  │   │                      │      │                     │  │  │
│  │   │  discord_bot.py      │      │  ChromaDB server    │  │  │
│  │   │  telegram_bot.py     │ HTTP │  :8000 (internal)   │  │  │
│  │   │  rag_engine.py  ─────┼─────►  Named volume:      │  │  │
│  │   │  BAAI/bge-m3 model   │      │  chroma_data        │  │  │
│  │   │  (HF cache volume)   │      │                     │  │  │
│  │   └──────────────────────┘      └─────────────────────┘  │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ./data/  (bind mount → /app/data, read-only)                   │
└─────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
   Discord / Telegram API          No public port
   (outbound only)                 ChromaDB stays
                                   internal only
```

> **Security note:** ChromaDB's port `8000` is never exposed to the host or internet. It is only reachable by containers on the `rag_net` bridge network.

---

### Request Flow

```
User sends message in Discord / Telegram
         │
         ▼
 ┌───────────────────┐
 │  discord_bot.py   │  1. Receives message (mention / DM / !ask)
 │  telegram_bot.py  │  2. Strips command prefix / mention tag
 └────────┬──────────┘  3. Runs RAG query in ThreadPoolExecutor
          │                (avoids blocking async event loop)
          ▼
 ┌───────────────────────────────────────────────┐
 │               rag_engine.py                   │
 │                                               │
 │  ┌─────────────────────────────────────────┐  │
 │  │  1. Embed question                      │  │
 │  │     BAAI/bge-m3 → 1024-dim vector       │  │
 │  └──────────────┬──────────────────────────┘  │
 │                 │                             │
 │  ┌──────────────▼──────────────────────────┐  │
 │  │  2. Similarity search                   │  │
 │  │     ChromaDB HttpClient                 │  │
 │  │     → Top-K relevant chunks             │  │
 │  └──────────────┬──────────────────────────┘  │
 │                 │                             │
 │  ┌──────────────▼──────────────────────────┐  │
 │  │  3. Augmented generation                │  │
 │  │     Gemini 2.5 Flash                    │  │
 │  │     (chunks + question → answer)        │  │
 │  └──────────────┬──────────────────────────┘  │
 └─────────────────┼─────────────────────────────┘
                   │
                   ▼
         Reply sent to user
```

---

### Indexing Flow (first run / re-index)

```
data/*.pdf
    │
    ▼
SimpleDirectoryReader          reads all PDFs into Document objects
    │
    ▼
LlamaIndex text splitter       chunks: 512 tokens, overlap: 50
    │
    ▼
BAAI/bge-m3 embedding          each chunk → 1024-dim dense vector
    │
    ▼
ChromaVectorStore.add()        vectors + metadata → ChromaDB (persisted)
    │
    ▼
storage volume: chroma_data    survives container restarts
```

---

### File Responsibilities

| File | Lines | Role |
|---|---|---|
| [src/main.py](src/main.py) | 25 | Entry point — reads `BOT_TYPE` env var, starts Discord or Telegram bot |
| [src/rag_engine.py](src/rag_engine.py) | ~85 | Configures models, connects ChromaDB, builds/loads index, exposes `query()` |
| [src/discord_bot.py](src/discord_bot.py) | 116 | Discord event handlers, `!ask` command, async bridge via `ThreadPoolExecutor` |
| [docker-compose.yml](docker-compose.yml) | — | Defines `chroma` + `bot` services, volumes, internal network |
| [Dockerfile](Dockerfile) | — | Builds the `bot` container image |
| `data/` | — | Drop your PDF files here (bind-mounted read-only into container) |

---

## Quick Start (Local)

```bash
# 1. Create virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env
cp .env.example .env   # or create manually — see Environment Variables below

# 4. Add PDFs
cp your_document.pdf data/

# 5. Run (requires a local or remote ChromaDB instance)
python src/main.py
```

For a full **Docker-based deployment** (recommended for production), see [GUIDE_DEPLOY.md](GUIDE_DEPLOY.md).

---

## Environment Variables

Defined in `.env` (gitignored):

| Variable | Required | Default | Description |
|---|---|---|---|
| `GOOGLE_API_KEY` | Yes | — | Google AI Studio API key for Gemini LLM |
| `DISCORD_TOKEN` | Yes* | — | Discord bot token |
| `TELEGRAM_BOT_TOKEN` | Yes* | — | Telegram bot token |
| `BOT_TYPE` | No | `discord` | Which bot to start: `discord` or `telegram` |
| `CHROMA_HOST` | No | `localhost` | ChromaDB server hostname |
| `CHROMA_PORT` | No | `8000` | ChromaDB server port |
| `CHROMA_COLLECTION` | No | `rag_documents` | ChromaDB collection name |

*At least one bot token is required depending on `BOT_TYPE`.

---

## Discord Bot Setup

### 1. Create the bot

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** → name it → **Create**
3. Go to **Bot** → **Reset Token** → copy → paste as `DISCORD_TOKEN` in `.env`

### 2. Enable required intents

On the **Bot** page, scroll to **Privileged Gateway Intents** and enable:

- **Message Content Intent** — required to read message text

### 3. Invite the bot to your server

1. **OAuth2 → URL Generator**
2. Scopes: `bot`
3. Bot Permissions: `Read Messages / View Channels`, `Send Messages`, `Read Message History`
4. Copy the generated URL → open in browser → select server → **Authorize**

---

## How to Use in Discord

| Method | Example |
|---|---|
| Mention in channel | `@YourBot What is the main topic?` |
| Direct Message | Send any message directly to the bot |
| Prefix command | `!ask Summarize chapter 2` |

---

## Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `DISCORD_TOKEN is not set` | Missing `.env` entry | Add `DISCORD_TOKEN=...` to `.env` |
| `GOOGLE_API_KEY` auth error | Invalid key | Check key at [aistudio.google.com](https://aistudio.google.com) |
| Bot online but doesn't respond | Message Content Intent off | Enable in Discord Developer Portal → Bot |
| `Connection refused` to ChromaDB | ChromaDB not running | Start with `docker compose up chroma` or check `CHROMA_HOST` |
| Answers seem wrong / outdated | PDF changed, index stale | Re-index — see [GUIDE_DEPLOY.md](GUIDE_DEPLOY.md#re-indexing) |
| Slow first response | `BAAI/bge-m3` loading (~1GB) | Normal — ~10–30s cold start; use `hf_cache` volume to avoid re-download |
