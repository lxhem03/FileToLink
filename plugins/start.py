import random
import humanize
import logging
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, CallbackQuery
from info import URL, LOG_CHANNEL, SHORTLINK, START_IMG
from urllib.parse import quote_plus
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size
from TechVJ.util.human_readable import humanbytes
from database.users_chats_db import db
from utils import temp, get_shortlink

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@Client.on_message(filters.private & filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    username = message.from_user.mention
    logger.info(f"/start command received from user: {user_id} ({username})")

    button = InlineKeyboardMarkup([
        [InlineKeyboardButton('• ᴀʙᴏᴜᴛ •', callback_data='about'),
            InlineKeyboardButton('• ʜᴇʟᴘ •', callback_data='help')],
        [InlineKeyboardButton("💝 Uᴘᴅᴀᴛᴇs 💝", url='https://telegram.me/The_TGguy')]
    ])

    try:
        if not await db.is_user_exist(user_id):
            await db.add_user(user_id, message.from_user.first_name)
            logger.info(f"New user added to DB: {user_id} - {message.from_user.first_name}")
            try:
                await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(user_id, username))
            except Exception as log_err:
                logger.error(f"Failed to send new user log: {log_err}")

        await client.send_message(
            chat_id=user_id,
            text=script.START_TXT.format(username),
            reply_markup=button,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error in /start for {user_id}: {e}", exc_info=True)
        try:
            await message.reply_text(
                text=f"{script.START_TXT.format(username)}",
                reply_markup=button,
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as fallback_err:
            logger.critical(f"Even fallback failed for {user_id}: {fallback_err}")


@Client.on_message(filters.private & (filters.document | filters.video))
async def stream_start(client, message):
    file = getattr(message, message.media.value)
    filename = file.file_name

    # ── FIX 1: Reject files with no filename ─────────────────────────────────
    if not filename or not filename.strip():
        await message.reply_text(
            "⚠️ <b>No filename found in the given file.</b>\n\n"
            "Please rename your file and try again.",
            parse_mode=enums.ParseMode.HTML,
            quote=True
        )
        return
    # ─────────────────────────────────────────────────────────────────────────

    filesize = humanize.naturalsize(file.file_size)
    fileid = file.file_id
    user_id = message.from_user.id
    username = message.from_user.mention

    log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)
    fileName = {quote_plus(get_name(log_msg))}

    if SHORTLINK == False:
        stream = f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
        download = f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
    else:
        stream = await get_shortlink(f"{URL}watch/{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}")
        download = await get_shortlink(f"{URL}{str(log_msg.id)}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}")

    await log_msg.reply_text(
        text=f"•• ʟɪɴᴋ ɢᴇɴᴇʀᴀᴛᴇᴅ ꜰᴏʀ ɪᴅ #{user_id} \n•• ᴜꜱᴇʀɴᴀᴍᴇ : {username} \n\n•• ᖴᎥᒪᗴ Nᗩᗰᗴ : {fileName}",
        quote=True,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🚀 Fast Download 🚀", url=download),
            InlineKeyboardButton('🖥️ Watch online 🖥️', url=stream)
        ]])
    )

    rm = InlineKeyboardMarkup([[
        InlineKeyboardButton("sᴛʀᴇᴀᴍ 🖥", url=stream),
        InlineKeyboardButton("ᴅᴏᴡɴʟᴏᴀᴅ 📥", url=download)
    ]])
    msg_text = (
        "<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 !</u></i>\n\n"
        "<b>📂 Fɪʟᴇ ɴᴀᴍᴇ :</b> <i>{}</i>\n\n"
        "<b>📦 Fɪʟᴇ ꜱɪᴢᴇ :</b> <i>{}</i>\n\n"
        "<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <code>{}</code>\n\n"
        "<b> 🖥ᴡᴀᴛᴄʜ  :</b> <code>{}</code>\n\n"
        "<b>🚸 Nᴏᴛᴇ : ʟɪɴᴋ ᴡᴏɴ'ᴛ ᴇxᴘɪʀᴇ ᴛɪʟʟ ɪ ᴅᴇʟᴇᴛᴇ</b>"
    )
    await message.reply_text(
        text=msg_text.format(get_name(log_msg), humanbytes(get_media_file_size(message)), download, stream),
        quote=True,
        disable_web_page_preview=True,
        reply_markup=rm
    )


@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data
    if data == "start":
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention),
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('• ᴀʙᴏᴜᴛ •', callback_data='about'),
                 InlineKeyboardButton('• ʜᴇʟᴘ •', callback_data='help')],
                [InlineKeyboardButton("💝 Uᴘᴅᴀᴛᴇs 💝", url='https://telegram.me/The_TGguy')]
            ])
        )
    elif data == "help":
        await query.message.edit_text(
            text=Txt.HELP_TXT,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about")],
                [InlineKeyboardButton("💥  ᴅᴏɴᴀᴛᴇ", callback_data="donate"),
                 InlineKeyboardButton("", callback_data="source")],
                [InlineKeyboardButton("💝 Uᴘᴅᴀᴛᴇs 💝", url="https://t.me/The_TGguy")],
                [InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start"),
                 InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]
            ])
        )
    elif data == "about":
        await query.message.edit_text(
            text=script.ABOUT_TXT,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• Sᴏᴜʀᴄᴇ •", callback_data="source"),
                 InlineKeyboardButton("", callback_data="devs")],
                [InlineKeyboardButton("💥  ᴅᴏɴᴀᴛᴇ", callback_data="donate")],
                [InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start")]
            ])
        )
    elif data == "source":
        await query.message.edit_text(
            text=script.SOURCE_TXT,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about"),
                 InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data="help")],
                [InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start")]
            ])
        )
    elif data == "devs":
        await query.message.edit_text(
            text=script.DEVS_TXT,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about"),
                 InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data="help")],
                [InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start")]
            ])
        )
    elif data == "donate":
        await query.message.edit_text(
            text=script.DONATE_TXT,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ʙᴀᴄᴋ", callback_data="start"),
                 InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data="close")]
            ])
        )
    elif data == "close":
        try:
            await query.message.delete()
            await query.message.reply_to_message.delete()
            await query.message.continue_propagation()
        except:
            await query.message.delete()
            await query.message.continue_propagation()
