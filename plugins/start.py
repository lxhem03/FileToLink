import random
import humanize
from Script import script
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ForceReply, CallbackQuery
from info import URL, LOG_CHANNEL, SHORTLINK, START_IMG
from urllib.parse import quote_plus
from TechVJ.util.file_properties import get_name, get_hash, get_media_file_size
from TechVJ.util.human_readable import humanbytes
from database.users_chats_db import db
from utils import temp, get_shortlink

@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
    button = InlineKeyboardMarkup([
        [InlineKeyboardButton('• ᴀʙᴏᴜᴛ •', callback_data='about'),
        InlineKeyboardButton('• ʜᴇʟᴘ •', callback_data='help')],
        [InlineKeyboardButton("💝 Uᴘᴅᴀᴛᴇs 💝", url='https://telegram.me/The_TGguy')]
    ])
    await client.send_photo(
        chat_id=message.from_user.id,
        photo=START_IMG,
        caption=script.START_TXT.format(message.from_user.mention),
        reply_markup=button,
        parse_mode=enums.ParseMode.HTML,
        disable_web_page_preview=True
    )
    return


@Client.on_message(filters.private & (filters.document | filters.video))
async def stream_start(client, message):
    file = getattr(message, message.media.value)
    filename = file.file_name
    filesize = humanize.naturalsize(file.file_size) 
    fileid = file.file_id
    user_id = message.from_user.id
    username =  message.from_user.mention 

    log_msg = await client.send_cached_media(
        chat_id=LOG_CHANNEL,
        file_id=fileid,
    )
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
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚀 Fast Download 🚀", url=download),  # we download Link
                                            InlineKeyboardButton('🖥️ Watch online 🖥️', url=stream)]])  # web stream Link
    )
    rm=InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("sᴛʀᴇᴀᴍ 🖥", url=stream),
                InlineKeyboardButton("ᴅᴏᴡɴʟᴏᴀᴅ 📥", url=download)
            ]
        ] 
    )
    msg_text = """<i><u>𝗬𝗼𝘂𝗿 𝗟𝗶𝗻𝗸 𝗚𝗲𝗻𝗲𝗿𝗮𝘁𝗲𝗱 !</u></i>\n\n<b>📂 Fɪʟᴇ ɴᴀᴍᴇ :</b> <i>{}</i>\n\n<b>📦 Fɪʟᴇ ꜱɪᴢᴇ :</b> <i>{}</i>\n\n<b>📥 Dᴏᴡɴʟᴏᴀᴅ :</b> <code>{}</code>\n\n<b> 🖥ᴡᴀᴛᴄʜ  :</b> <code>{}</code>\n\n<b>🚸 Nᴏᴛᴇ : ʟɪɴᴋ ᴡᴏɴ'ᴛ ᴇxᴘɪʀᴇ ᴛɪʟʟ ɪ ᴅᴇʟᴇᴛᴇ</b>"""

    await message.reply_text(text=msg_text.format(get_name(log_msg), humanbytes(get_media_file_size(message)), download, stream), quote=True, disable_web_page_preview=True, reply_markup=rm)


@Client.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    data = query.data 
    if data == "start":
        await query.message.edit_text(
            text=script.START_TXT.format(query.from_user.mention),
            disable_web_page_preview=True,
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton('• ᴀʙᴏᴜᴛ •', callback_data='about'),
                InlineKeyboardButton('• ʜᴇʟᴘ •', callback_data='help')],
                [InlineKeyboardButton("💝 Uᴘᴅᴀᴛᴇs 💝", url='https://telegram.me/The_TGguy')]
            ])
        )
    elif data == "help":
        await query.message.edit_text(
            text=Txt.HELP_TXT,
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup([
		[InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data = "about")],
                [InlineKeyboardButton("💥  ᴅᴏɴᴀᴛᴇ", callback_data = "donate"),
                InlineKeyboardButton("", callback_data = "source")],
		[InlineKeyboardButton("💝 Uᴘᴅᴀᴛᴇs 💝", url="https://t.me/The_TGguy")],
		[InlineKeyboardButton("ʜᴏᴍᴇ", callback_data = "start"),
         InlineKeyboardbutton("ᴄʟᴏsᴇ", callback_data="close"]
            ])            
    )

    
    elif data == "about":
        await query.message.edit_text(
            text=script.ABOUT_TXT,
            disable_web_page_preview = True,
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
            disable_web_page_preview = True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about"),
                InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data="help")],
		[InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start")]
            ])            
        )    
	    
    elif data == "devs":
        await query.message.edit_text(
            text=script.DEVS_TXT,
            disable_web_page_preview = True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("• ᴀʙᴏᴜᴛ •", callback_data="about"),
                InlineKeyboardButton("• ʜᴇʟᴘ •", callback_data="help")],
		[InlineKeyboardButton("ʜᴏᴍᴇ", callback_data="start")]
            ])            
        )    
	    
    elif data == "donate":
        await query.message.edit_text(
            text=script.DONATE_TXT,
            disable_web_page_preview = True,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("ʙᴀᴄᴋ", callback_data = "start"),
                InlineKeyboardButton("ᴄʟᴏsᴇ", callback_data = "close")]
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
        
