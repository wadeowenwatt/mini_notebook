# Mini Notebook — Discord RAG Bot

## Project Overview

A RAG (Retrieval-Augmented Generation) chatbot that answers questions about PDF documents via Discord. Users drop PDFs into `data/`, the system builds a vector index, and a Discord bot serves answers using semantic search + Google Gemini.

## Tech Stack

- **Language:** Python 3.10+
- **RAG Framework:** LlamaIndex (`llama-index-core 0.14.x`)
- **LLM:** Google Gemini 2.5 Flash via `llama-index-llms-google-genai`
- **Embeddings:** `BAAI/bge-m3` via `llama-index-embeddings-huggingface` (local, runs on PyTorch)
- **Bot Interface:** discord.py 2.3
- **Config:** python-dotenv (`.env` file)
- **Vector Storage:** LlamaIndex's built-in JSON-based persistent store (local disk)

## Project Structure

```
mini_notebook/
├── src/
│   ├── main.py            # Entry point — starts the Discord bot
│   ├── rag_engine.py      # RAG pipeline: PDF ingestion, embedding, vector search, LLM query
│   ├── discord_bot.py     # Discord event handlers, !ask command, async bridge
│   └── telegram_bot.py    # Telegram event handlers
├── data/              # Place PDF files here (input documents)
├── storage/           # Auto-generated vector index cache (JSON files)
├── requirements.txt   # Pinned dependencies (pip freeze output)
├── .env               # API keys (GOOGLE_API_KEY, DISCORD_TOKEN) — gitignored
└── README.md          # Full setup guide with Discord bot configuration steps
```

## Essential Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run
python src/main.py

# Quick RAG test (no Discord needed)
python -c "import sys; sys.path.insert(0, 'src'); import rag_engine; print(rag_engine.query('What is this document about?'))"

# Re-index after changing PDFs
rm -rf storage/ && python src/main.py
```

## Environment Variables

Defined in `.env` (gitignored). Required keys:

| Variable               | Purpose                                 |
| ---------------------- | --------------------------------------- |
| `GOOGLE_API_KEY`       | Google AI Studio API key for Gemini LLM |
| `DISCORD_TOKEN`        | Discord bot token                       |
| `ZALO_OA_ACCESS_TOKEN` | _(Optional)_ Zalo OA integration        |

## Key File Responsibilities

| File                                     | Lines | What it does                                                                                                         |
| ---------------------------------------- | ----- | -------------------------------------------------------------------------------------------------------------------- |
| [src/rag_engine.py](src/rag_engine.py)   | 78    | Configures LLM + embeddings (`Settings` global), builds/loads vector index, exposes `query()` API                    |
| [src/discord_bot.py](src/discord_bot.py) | 116   | Async Discord bot with `on_message` handler + `!ask` prefix command, bridges sync RAG calls via `ThreadPoolExecutor` |
| [src/main.py](src/main.py)               | 5     | Thin entry point calling `discord_bot.run()`                                                                         |

## Important Behaviors

- **Index auto-build:** On first run (no `storage/` dir), `rag_engine` reads all PDFs from `data/` and persists the index. Subsequent runs load from `storage/` instantly. See [src/rag_engine.py:57](src/rag_engine.py#L57).
- **Module-level initialization:** The vector index and query engine are created at **import time** as module globals. See [src/rag_engine.py:56-58](src/rag_engine.py#L56-L58).
- **Re-indexing:** Delete `storage/` and restart. There is no incremental update mechanism.

## Additional Documentation

When working on this codebase, check these docs for relevant patterns:

| Topic                                     | File                                                                             |
| ----------------------------------------- | -------------------------------------------------------------------------------- |
| Architectural patterns & design decisions | [.claude/docs/architectural_patterns.md](.claude/docs/architectural_patterns.md) |
| Discord bot setup & OAuth2 configuration  | [README.md](README.md) (sections 2–3)                                            |
| Common issues & troubleshooting           | [README.md](README.md) (section 8)                                               |
