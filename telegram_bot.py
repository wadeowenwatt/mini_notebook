import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv

import rag_engine  # noqa: F401 – triggers model loading at startup

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ThreadPoolExecutor to run LlamaIndex query (sync) without blocking the event loop
_executor = ThreadPoolExecutor(max_workers=4)

# ─── Handlers ────────────────────────────────────────────────────────────────


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggered on every text message sent to the bot (private or group).

    In groups, the bot only responds when directly mentioned (@bot).
    In private chats, it responds to all messages.
    """
    message = update.message
    if message is None:
        return

    user_text = message.text or ""
    bot_username = context.bot.username

    is_private = message.chat.type == "private"
    is_mentioned = f"@{bot_username}" in user_text

    if not is_private and not is_mentioned:
        return

    # Strip the mention tag from the message content if present
    if is_mentioned and bot_username:
        user_text = user_text.replace(f"@{bot_username}", "").strip()

    if not user_text:
        await message.reply_text(
            "Bạn muốn hỏi gì? Hãy nhắn tin cho mình nhé!\n"
            "*(What would you like to ask? Send me a message!)*"
        )
        return

    print(f"[Telegram] {message.from_user.username} asked: {user_text!r}")

    await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")

    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(_executor, rag_engine.query, user_text)

    print(f"[Telegram] Answer: {answer[:120]}...")
    await message.reply_text(answer)


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Command handler: /ask <your question>

    Works in any chat without needing a mention.
    Example: /ask What is the main topic of the document?
    """
    message = update.message
    if message is None:
        return

    question = " ".join(context.args) if context.args else ""

    if not question:
        await message.reply_text(
            "Cách dùng: /ask <câu hỏi>\n"
            "Ví dụ: /ask Nội dung chính của tài liệu là gì?"
        )
        return

    print(f"[Telegram] /ask from {message.from_user.username}: {question!r}")

    await context.bot.send_chat_action(chat_id=message.chat_id, action="typing")

    loop = asyncio.get_event_loop()
    answer = await loop.run_in_executor(_executor, rag_engine.query, question)

    print(f"[Telegram] Answer: {answer[:120]}...")
    await message.reply_text(answer)


# ─── Entry Point ─────────────────────────────────────────────────────────────


def run():
    """Start the Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. "
            "Please add TELEGRAM_BOT_TOKEN=<your-token> to your .env file."
        )

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))

    print("[Telegram] Bot is starting...")
    app.run_polling()
