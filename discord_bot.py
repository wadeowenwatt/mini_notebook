import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

import discord
from discord.ext import commands
from dotenv import load_dotenv

import rag_engine  # noqa: F401 – triggers model loading at startup

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")

# ThreadPoolExecutor to run LlamaIndex query (sync) without
# blocking the Discord event loop or causing asyncio conflicts
_executor = ThreadPoolExecutor(max_workers=4)

# ─── Bot Setup ───────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True  # Required to read message content

bot = commands.Bot(command_prefix="!", intents=intents)

# ─── Events ──────────────────────────────────────────────────────────────────


@bot.event
async def on_ready():
    print(f"[Discord] Logged in as {bot.user} (ID: {bot.user.id})")
    print("[Discord] Bot is ready and listening for messages.")


@bot.event
async def on_message(message: discord.Message):
    """
    Triggered on every message the bot can see.

    The bot responds when:
      - The message is NOT from the bot itself.
      - Either the bot is mentioned (@bot) OR the message is a Direct Message.
    """
    # Ignore messages sent by the bot itself to avoid infinite loops
    if message.author == bot.user:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    is_mentioned = bot.user in message.mentions

    if not is_dm and not is_mentioned:
        # Allow command processing (e.g. !ask) to still work in guilds
        await bot.process_commands(message)
        return

    # Strip the mention tag from the message content if present
    user_text = message.content
    if is_mentioned:
        user_text = user_text.replace(f"<@{bot.user.id}>", "").replace(
            f"<@!{bot.user.id}>", ""
        ).strip()

    if not user_text:
        await message.reply(
            "Bạn muốn hỏi gì? Hãy nhắn tin cho mình nhé! 😊\n"
            "*(What would you like to ask? Send me a message!)*"
        )
        return

    print(f"[Discord] {message.author} asked: {user_text!r}")

    # Show typing indicator while processing
    async with message.channel.typing():
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(_executor, rag_engine.query, user_text)

    print(f"[Discord] Answer: {answer[:120]}...")
    await message.reply(answer)

    # Ensure prefix commands still work
    await bot.process_commands(message)


# ─── Slash / Prefix Command ──────────────────────────────────────────────────


@bot.command(name="ask")
async def ask_command(ctx: commands.Context, *, question: str):
    """
    Prefix command: !ask <your question>

    Works in any channel the bot has access to, without needing a mention.
    Example: !ask What is the main topic of the document?
    """
    print(f"[Discord] !ask from {ctx.author}: {question!r}")

    async with ctx.typing():
        loop = asyncio.get_event_loop()
        answer = await loop.run_in_executor(_executor, rag_engine.query, question)

    print(f"[Discord] Answer: {answer[:120]}...")
    await ctx.reply(answer)


# ─── Entry Point ─────────────────────────────────────────────────────────────


def run():
    """Start the Discord bot."""
    if not DISCORD_TOKEN:
        raise RuntimeError(
            "DISCORD_TOKEN is not set. "
            "Please add DISCORD_TOKEN=<your-token> to your .env file."
        )
    bot.run(DISCORD_TOKEN)
