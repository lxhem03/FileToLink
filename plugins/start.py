import humanize
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from info import URL, LOG_CHANNEL, SHORTLINK, START_IMG
from urllib.parse import quote_plus, unquote_plus
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size
from TechVJ.util.human_readable import humanbytes
from database.users_chats_db import db
from utils import temp, get_shortlink


def user_link(user) -> str:
    """
    Returns a clickable HTML mention for any user — whether or not they
    have a @username.  Always produces: <a href="tg://user?id=ID">Name</a>
    """
    name = (user.first_name or "") + (" " + user.last_name if user.last_name else "")
    name = name.strip() or str(user.id)
    return f'<a href="tg://user?id={user.id}">{name}</a>'


@Client.on_message(filters.private & filters.command("start"))
async def start(client, message):
    user_id = message.from_user.id
    username = message.from_user.mention

    button = InlineKeyboardMarkup([
        [InlineKeyboardButton('• ᴀʙᴏᴜᴛ •', callback_data='about'),
         InlineKeyboardButton('• ʜᴇʟᴘ •', callback_data='help')],
        [InlineKeyboardButton("💝 Uᴘᴅᴀᴛᴇs 💝", url='https://telegram.me/The_TGguy')]
    ])

    try:
        if not await db.is_user_exist(user_id):
            await db.add_user(user_id, message.from_user.first_name)
            try:
                await client.send_message(
                    LOG_CHANNEL,
                    script.LOG_TEXT_P.format(user_id, username)
                )
            except Exception:
                pass

        await client.send_message(
            chat_id=user_id,
            text=script.START_TXT.format(username),
            reply_markup=button,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True
        )

    except Exception:
        try:
            await message.reply_text(
                text=script.START_TXT.format(username),
                reply_markup=button,
                parse_mode=enums.ParseMode.HTML
            )
        except Exception:
            pass


@Client.on_message(filters.private & (filters.document | filters.video))
async def stream_start(client, message):
    file = getattr(message, message.media.value)
    filename = file.file_name

    # Reject files with no filename
    if not filename or not filename.strip():
        await message.reply_text(
            "⚠️ <b>No filename found in the given file.</b>\n\n"
            "Please rename your file and try again.",
            parse_mode=enums.ParseMode.HTML,
            quote=True
        )
        return

    fileid   = file.file_id
    user_id  = message.from_user.id
    mention  = user_link(message.from_user)   # always a clickable link

    log_msg = await client.send_cached_media(chat_id=LOG_CHANNEL, file_id=fileid)

    # Clean readable filename — decode percent-encoding for display
    clean_name = unquote_plus(get_name(log_msg))
    file_size  = humanbytes(get_media_file_size(message))

    if not SHORTLINK:
        stream   = f"{URL}watch/{log_msg.id}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
        download = f"{URL}{log_msg.id}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}"
    else:
        stream   = await get_shortlink(f"{URL}watch/{log_msg.id}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}")
        download = await get_shortlink(f"{URL}{log_msg.id}/{quote_plus(get_name(log_msg))}?hash={get_hash(log_msg)}")

    # ── Log channel reply (clean, readable, HTML) ──────────────────────
    log_text = (
        f"🔗 <b>Link Generated</b>\n\n"
        f"👤 <b>User:</b> {mention} (<code>{user_id}</code>)\n"
        f"📂 <b>File:</b> <code>{clean_name}</code>\n"
        f"📦 <b>Size:</b> {file_size}"
    )
    await log_msg.reply_text(
        text=log_text,
        quote=True,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🚀 Download", url=download),
            InlineKeyboardButton("🖥️ Watch", url=stream)
        ]])
    )

    # ── Reply to the user ──────────────────────────────────────────────
    user_text = (
        f"<i><u>✅ Your Link is Ready!</u></i>\n\n"
        f"📂 <b>File:</b> <i>{clean_name}</i>\n"
        f"📦 <b>Size:</b> <i>{file_size}</i>\n\n"
        f"📥 <b>Download:</b>\n<code>{download}</code>\n\n"
        f"🖥 <b>Watch Online:</b>\n<code>{stream}</code>\n\n"
        f"<b>🚸 Note: Link won't expire till I delete the file</b>"
    )
    await message.reply_text(
        text=user_text,
        quote=True,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🖥 Stream", url=stream),
            InlineKeyboardButton("📥 Download", url=download)
        ]])
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
            text=script.HELP_TXT,
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about")],
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
                [InlineKeyboardButton("• Sᴏᴜʀᴄᴇ •", callback_data="source")],
                [InlineKeyboardButton("💥 ᴅᴏɴᴀᴛᴇ", callback_data="donate")],
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
        except Exception:
            await query.message.delete()
