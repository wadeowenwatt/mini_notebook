# Architectural Patterns & Design Decisions

## 1. Two-Layer Architecture: Engine + Interface

The codebase cleanly separates **RAG logic** from **interface/delivery**:

- **Engine layer** (`src/rag_engine.py`): Stateless query function, no knowledge of Discord/HTTP/etc.
- **Interface layer** (`src/discord_bot.py`): Handles protocol-specific concerns (messages, mentions, typing indicators), delegates all intelligence to the engine.

This makes it straightforward to add new interfaces (web UI, Zalo bot, CLI) without touching RAG logic — just import `rag_engine.query()`.

**References:**

- Engine's public API: [src/rag_engine.py:63-77](../src/rag_engine.py#L63-L77) — single `query(message: str) -> str` function
- Interface consuming it: [src/discord_bot.py:75](../src/discord_bot.py#L75) and [src/discord_bot.py:99](../src/discord_bot.py#L99)

---

## 2. Module-Level Singleton Initialization

Heavy resources (LLM client, embedding model, vector index) are initialized **once at module import time** as module-level globals, rather than per-request:

```
# Pattern: initialize once, use everywhere
_index = _load_index() if os.path.exists(PERSIST_DIR) else _build_index()
_query_engine = _index.as_query_engine()
```

**Why:** Embedding model loading (`BAAI/bge-m3`) takes 10–30s. Module-level init ensures this cost is paid once at startup, not per query.

**Trade-off:** Makes the module non-importable without side effects. The Discord bot explicitly imports `rag_engine` at startup to trigger this: [src/discord_bot.py:9](../src/discord_bot.py#L9).

**References:**

- Global config: [src/rag_engine.py:21-27](../src/rag_engine.py#L21-L27)
- Singleton creation: [src/rag_engine.py:56-58](../src/rag_engine.py#L56-L58)

---

## 3. Sync-in-Async Bridge via ThreadPoolExecutor

LlamaIndex's `query()` is synchronous and CPU/IO-bound. The Discord bot runs on asyncio. The bridge pattern used:

1. Create a shared `ThreadPoolExecutor(max_workers=4)` — [src/discord_bot.py:17](../src/discord_bot.py#L17)
2. In async handlers, offload sync calls via `loop.run_in_executor()` — [src/discord_bot.py:74-75](../src/discord_bot.py#L74-L75)

**Why not `asyncio.to_thread()`?** The explicit executor gives control over concurrency limits (4 workers = max 4 concurrent RAG queries).

**Convention:** All sync-to-async bridging goes through `_executor`. This pattern should be replicated for any new interface that uses asyncio.

---

## 4. Build-or-Load Index with Filesystem Check

The index management follows a simple "cache on disk" pattern:

1. Check if `storage/` directory exists
2. If yes → load serialized index from JSON files
3. If no → read PDFs from `data/`, build index, persist to `storage/`

**References:**

- Decision point: [src/rag_engine.py:57](../src/rag_engine.py#L57)
- Build path: [src/rag_engine.py:32-44](../src/rag_engine.py#L32-L44)
- Load path: [src/rag_engine.py:47-53](../src/rag_engine.py#L47-L53)

**No incremental updates.** Changing PDFs requires deleting `storage/` manually. This is by design for simplicity.

---

## 5. Configuration via LlamaIndex Global Settings

Rather than passing config to each component, the codebase uses LlamaIndex's `Settings` singleton:

```
Settings.llm = llm
Settings.embed_model = embed_model
Settings.chunk_size = 512
Settings.chunk_overlap = 50
```

All LlamaIndex components (indexer, query engine) implicitly pick up these settings.

**References:** [src/rag_engine.py:24-27](../src/rag_engine.py#L24-L27)

---

## 6. Environment-Based Secret Management

All secrets live in `.env` (gitignored), loaded via `python-dotenv`:

- `rag_engine.py` loads `.env` for `GOOGLE_API_KEY` (used implicitly by `google-genai`)
- `discord_bot.py` loads `.env` for `DISCORD_TOKEN` (used explicitly)

**Convention:** Each module that needs env vars calls `load_dotenv()` independently. Validation happens at the point of use (e.g., [src/discord_bot.py:110-114](../src/discord_bot.py#L110-L114) raises `RuntimeError` if token is missing).

---

## 7. Thin Entry Point Pattern

`main.py` is intentionally minimal (5 lines) — it only imports and calls `run()`:

```python
from discord_bot import run

if __name__ == "__main__":
    run()
```

**Why:** Keeps the entry point swappable. To switch from Discord to a web server, only `main.py` changes. The engine and bot modules remain decoupled.

**Reference:** [src/main.py:1-4](../src/main.py#L1-L4)
