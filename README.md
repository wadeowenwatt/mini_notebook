# Mini Notebook — Discord RAG Bot

A **Google Notebook-inspired** chatbot that lets you ask questions about your PDF documents directly in Discord.

Upload a PDF → the system embeds it into a vector store → users ask questions in Discord → the bot retrieves relevant chunks and answers with Google Gemini.

---

## Architecture

```
Discord Message
      │
      ▼
 discord_bot.py        ← receives message, strips @mention
      │
      ▼
  rag_engine.py        ← vector search (BAAI/bge-m3) + LLM answer (Gemini 2.5 Flash)
      │
      ├── storage/     ← persisted vector index (auto-built on first run)
      └── data/        ← your PDF files go here
```

| File | Role |
|---|---|
| `main.py` | Entry point — starts the Discord bot |
| `discord_bot.py` | Discord event handlers and `!ask` command |
| `rag_engine.py` | PDF loading, embedding, vector search, LLM query |
| `data/` | Drop your PDF files here |
| `storage/` | Auto-generated vector index cache |

---

## Prerequisites

- Python 3.10+
- A **Google AI Studio** API key → [aistudio.google.com](https://aistudio.google.com)
- A **Discord Bot** token (see setup below)

---

## 1. Environment Variables

Create a `.env` file in the project root:

```env
GOOGLE_API_KEY=your_google_api_key_here
DISCORD_TOKEN=your_discord_bot_token_here
```

---

## 2. Discord Bot Setup

### 2.1 Create the bot

1. Go to [discord.com/developers/applications](https://discord.com/developers/applications)
2. Click **New Application** → give it a name → **Create**
3. Go to **Bot** (left sidebar) → click **Add Bot**
4. Under **Token** → click **Reset Token** → copy the token → paste into `.env` as `DISCORD_TOKEN`

### 2.2 Enable required intents

Still on the **Bot** page, scroll to **Privileged Gateway Intents** and turn on:

- ✅ **Message Content Intent** — required to read what users type

### 2.3 Invite the bot to your server

1. Go to **OAuth2 → URL Generator** (left sidebar)
2. Under **Scopes**, check: `bot`
3. Under **Bot Permissions**, check:
   - `Read Messages / View Channels`
   - `Send Messages`
   - `Read Message History`
4. Copy the generated URL → open in browser → select your server → **Authorize**

---

## 3. Installation

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## 4. Add Your PDF

Place one or more PDF files inside the `data/` folder:

```
data/
└── your_document.pdf
```

> **First run:** the bot will read the PDFs, generate embeddings, and save them to `storage/`. This may take a minute depending on PDF size.
>
> **Subsequent runs:** the index is loaded instantly from `storage/` — no re-embedding needed.
>
> **Changed PDFs?** Delete the `storage/` folder and restart the bot to rebuild the index.

---

## 5. Run the Bot

```bash
python main.py
```

Expected startup output:

```
[RAG] Phát hiện dữ liệu đã embedding, đang tải lên từ ổ cứng...
[RAG] Tải embedding thành công!
[Discord] Logged in as YourBotName#1234 (ID: 123456789)
[Discord] Bot is ready and listening for messages.
```

---

## 6. How to Use in Discord

The bot supports three interaction modes:

### Mention in a server channel
```
@YourBot What is the main topic of the document?
```

### Direct Message (DM)
Send any message directly to the bot — no mention needed.

### Prefix command `!ask`
Works in any channel the bot has access to, without requiring a mention:
```
!ask Summarize the key points from chapter 2
```

---

## 7. Testing

### 7.1 Test the RAG engine directly (no Discord needed)

Run a quick query from the terminal to verify the PDF was indexed correctly and the LLM responds:

```bash
python - <<'EOF'
import rag_engine
answer = rag_engine.query("What is this document about?")
print(answer)
EOF
```

You should see `[RAG]` log lines followed by the answer printed to the terminal.

### 7.2 Test the Discord bot end-to-end

1. Start the bot: `python main.py`
2. In Discord, send to the bot (DM or mention):
   ```
   What is this document about?
   ```
3. Confirm the bot replies with a relevant answer.
4. Check the terminal — you should see:
   ```
   [Discord] YourName#0000 asked: 'What is this document about?'
   [RAG] Query: 'What is this document about?'
   [RAG] Answer: ...
   [Discord] Answer: ...
   ```

### 7.3 Test the `!ask` command

In any server channel the bot can see:
```
!ask List the main sections of the document
```

### 7.4 Test with a new PDF (re-index)

```bash
# 1. Replace the PDF in data/
cp /path/to/new_document.pdf data/

# 2. Delete the old index
rm -rf storage/

# 3. Restart — the bot will rebuild the index automatically
python main.py
```

---

## 8. Common Issues

| Symptom | Cause | Fix |
|---|---|---|
| `DISCORD_TOKEN is not set` | Missing or empty `.env` | Add `DISCORD_TOKEN=...` to `.env` |
| `GOOGLE_API_KEY` auth error | Missing or invalid key | Add `GOOGLE_API_KEY=...` to `.env` |
| Bot is online but doesn't respond | Message Content Intent disabled | Enable it in Discord Developer Portal → Bot → Privileged Gateway Intents |
| Bot doesn't appear in server | Not invited correctly | Re-run the OAuth2 URL Generator with `bot` scope + correct permissions |
| `FileNotFoundError: data/` | No PDF in `data/` folder | Add at least one PDF to `data/` |
| Answers seem outdated or wrong | PDF changed but index not rebuilt | Delete `storage/` and restart |
| Slow first response | Embedding model loading (`BAAI/bge-m3`) | Normal — takes ~10–30s on first load |
