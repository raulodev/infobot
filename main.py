import html
import json
import logging
import traceback
from datetime import timedelta
from functools import wraps
from random import choice
from uuid import uuid4

import filetype
from decouple import config
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.constants import ChatAction, ChatType, MessageOriginType, ParseMode
from telegram.error import TimedOut
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

from utils import chunks, create_zip, file_size, make_thumbnail, resize_image, text_html

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


BOT_TOKEN = config("BOT_TOKEN")
DEVELOPER_CHAT_ID = config("DEVELOPER_CHAT_ID", default=None)


def send_action(action):
    """Sends `action` while processing func command."""

    def decorator(func):
        @wraps(func)
        async def handler(update, context, *args, **kwargs):
            await context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id, action=action
            )
            return await func(update, context, *args, **kwargs)

        return handler

    return decorator


def forwarded_messages(update: Update):
    """Process forwarded messages"""

    logger.info("Forwarded messages: %s", update.message.forward_origin)

    if not update.message.forward_origin:
        return None

    if update.message.forward_origin.type == ChatType.CHANNEL:
        channel = update.message.forward_origin.chat

        return text_html(
            [
                ("🔊Channel", channel.title),
                ("Username", channel.username),
                ("ID", channel.id),
                ("Message ID", update.message.forward_origin.message_id),
            ]
        )

    if update.message.forward_origin.type == MessageOriginType.USER:

        user = update.message.forward_origin.sender_user

        emoji = "🤖" if user.is_bot else "👤"

        return text_html(
            [
                (f"{emoji}Name", user.first_name),
                ("Username", f"@{user.username}" if user.username else "-"),
                ("ID", user.id),
            ]
        )

    if update.message.forward_origin.type == MessageOriginType.HIDDEN_USER:

        return text_html(
            [
                ("👤Name", update.message.forward_origin.sender_user_name),
            ]
        )


@send_action(ChatAction.TYPING)
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    logger.info("Start command: %s", update.effective_user)

    await update.message.reply_sticker(
        sticker="CAACAgEAAxkBAAIBdWERw-axEySQ7ofMjO_YXEnObBThAAL3BwAC43gEAAHKoBGRYVqPJCAE"
    )

    await update.message.reply_text(
        text=f"<b>I'am ready {update.effective_user.first_name} send the message.</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="⭐️Rateme", url="https://t.me/BotsArchive/2158"
                    ),
                    InlineKeyboardButton(text="Your info", switch_inline_query="i"),
                ],
                [
                    InlineKeyboardButton(text="ℹ", callback_data="info"),
                ],
            ]
        ),
    )


async def info_btn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    await update.callback_query.edit_message_text(
        text=(
            "<b>ℹ️Information:</b>\n\n"
            '👨‍💻Creator: <a href="https://github.com/raulodev">raulodev</a>\n'
            '💻Repo: <a href="https://github.com/raulodev/infobot">Github</a>\n'
            '📣Channel: <a href="https://t.me/raulodev">raulodev channel</a>'
        ),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    query = update.inline_query.query

    if not query:
        return

    text = text_html(
        [
            ("👤Name", update.effective_user.first_name),
            ("Username", update.effective_user.username),
            ("ID", update.effective_user.id),
        ]
        if update.effective_user.username
        else [
            ("👤Name", update.effective_user.first_name),
            ("ID", update.effective_user.id),
        ]
    )

    results = [
        InlineQueryResultArticle(
            id=str(uuid4()),
            title="Tap to share your user information",
            input_message_content=InputTextMessageContent(text, parse_mode="html"),
            thumbnail_url="http://chilp.it/94322a1",
            thumbnail_width=5,
            thumbnail_height=5,
        )
    ]

    await update.inline_query.answer(results=results, is_personal=True, cache_time=0)


@send_action(ChatAction.TYPING)
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    text = text_html(
        [
            ("👤Name", update.effective_user.first_name),
            ("Username", update.effective_user.username),
            ("ID", update.effective_user.id),
            ("Lang", update.effective_user.language_code),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


async def sticker_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    sticker = update.message.sticker

    logger.info("Sticker: %s", sticker)

    file = await update.message.effective_attachment.get_file()

    file_bytearray = await file.download_as_bytearray()

    if not sticker.is_animated:

        await context.bot.send_chat_action(
            chat_id=update.effective_message.chat_id, action=ChatAction.UPLOAD_PHOTO
        )
        await update.message.reply_photo(photo=bytes(file_bytearray))

    else:
        await context.bot.send_chat_action(
            chat_id=update.effective_message.chat_id, action=ChatAction.TYPING
        )

    text = text_html(
        [
            ("🎨Sticker ID", sticker.file_id),
            ("Emoji", sticker.emoji),
            ("Set Name", sticker.set_name),
            ("Link Set", f"https://t.me/addstickers/{sticker.set_name}"),
            ("Size", file_size(sticker.file_size)),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="⬇️ Download pack", callback_data=f"ds:{sticker.set_name}"
                    )
                ]
            ]
        ),
    )


@send_action(ChatAction.TYPING)
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    logger.info("Photo: %s", update.message.photo)

    photo = update.message.photo[-1]

    text = text_html(
        [
            ("🖼Photo", None),
            ("Height", photo.height),
            ("Width", photo.width),
            ("Size", file_size(photo.file_size)),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


@send_action(ChatAction.TYPING)
async def animation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    logger.info("Animation: %s", update.message.animation)

    animation = update.message.animation

    text = text_html(
        [
            ("🎬Animation", None),
            ("Duration", timedelta(seconds=animation.duration)),
            ("Size", file_size(animation.file_size)),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


@send_action(ChatAction.TYPING)
async def audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    logger.info("Audio: %s", update.message.audio)

    audio = update.message.audio

    text = text_html(
        [
            ("🎧Audio", None),
            ("FileName", audio.file_name),
            ("Duration", timedelta(seconds=audio.duration)),
            ("Size", file_size(audio.file_size)),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


@send_action(ChatAction.TYPING)
async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    logger.info("Document: %s", update.message.document)

    document = update.message.document

    text = text_html(
        [
            ("📄Document", None),
            ("Doc. Name", document.file_name),
            ("Size", file_size(document.file_size)),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


@send_action(ChatAction.TYPING)
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    logger.info("Video: %s", update.message.video)

    video = update.message.video

    text = text_html(
        [
            ("📼Video", None),
            ("Duration", timedelta(seconds=video.duration)),
            ("Size", file_size(video.file_size)),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


@send_action(ChatAction.TYPING)
async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    logger.info("Voice: %s", update.message.voice)

    voice = update.message.voice

    text = text_html(
        [
            ("🎤Voice", None),
            ("Duration", timedelta(seconds=voice.duration)),
            ("Size", file_size(voice.file_size)),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


@send_action(ChatAction.TYPING)
async def dice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    logger.info("Dice: %s", update.message.dice)

    dice = update.message.dice

    text = text_html(
        [
            ("🎲Dice", None),
            ("Emoji", dice.emoji),
            ("Value", dice.value),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


@send_action(ChatAction.TYPING)
async def poll_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    forwarded_info = forwarded_messages(update)

    logger.info("Poll: %s", update.message.poll)

    poll = update.message.poll

    content = [
        ("📊Poll", None),
        ("Type", poll.type),
        ("Question", poll.question),
        ("Anonymous", "Yes" if poll.is_anonymous else "No"),
        ("Mult. Answers", "Yes" if poll.allows_multiple_answers else "No"),
        ("Options", len(poll.options)),
    ]

    for option in poll.options:
        content.append((option.text, option.voter_count))

    text = text_html(content)

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


@send_action(ChatAction.CHOOSE_STICKER)
async def download_pack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    set_name = update.callback_query.data.split(":")[1]

    logger.info("Download pack: %s", set_name)

    try:
        sticker_set = await context.bot.get_sticker_set(name=set_name)

        logger.info("Sticker set: %s", sticker_set)
    except TimedOut:
        logger.error("Timed out while getting the sticker set")
        await update.callback_query.message.reply_text(
            text="❌ Error while getting the sticker set"
        )
        return

    await update.callback_query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="⏳ Downloading...", callback_data="wait")]]
        )
    )

    part_number = 1
    for part in chunks(sticker_set.stickers, 30):

        stickers = []

        logger.info("Downloading stickers")

        for index, sticker in enumerate(part, start=1):
            try:
                sticker_file = await sticker.get_file()
                sticker_file_bytearray = await sticker_file.download_as_bytearray()
                sticker_file_type = filetype.guess(sticker_file_bytearray)
                sticker_file_extension = sticker_file_type.extension

            except TimedOut:
                logger.error("Timed out while getting the sticker file")
                continue

            image = await resize_image(sticker_file_bytearray)

            # Maybe the sticker is not an image
            if not image:
                logger.info("Image type: %s", sticker_file_type.mime)
                logger.info("Sticker %s", sticker)

                if DEVELOPER_CHAT_ID:
                    await context.bot.send_message(
                        chat_id=DEVELOPER_CHAT_ID,
                        text="🚫 Error while resizing the sticker",
                    )
                    await context.bot.send_sticker(
                        chat_id=DEVELOPER_CHAT_ID, sticker=sticker
                    )

                continue

            filename = f"sticker_{index}.{sticker_file_extension}"
            image.name = filename

            stickers.append({"filename": filename, "file": image})

            if index == len(part):

                logger.info("Making thumbnail")
                thumbnail = None
                while not thumbnail:
                    thumbnail = await make_thumbnail(choice(stickers)["file"].read())

                stickers.append({"filename": "thumbnail.png", "file": thumbnail})

        zip_buffer = await create_zip(
            set_name=set_name,
            part=part_number,
            title=sticker_set.title,
            bot_username=context.bot.username,
            stickers=stickers,
        )
        part_number += 1

        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_message.chat_id,
                action=ChatAction.UPLOAD_DOCUMENT,
            )

            logger.info("Sending zip file")

            await update.callback_query.message.reply_document(
                document=zip_buffer,
                caption=(
                    "1. Install Sticker Maker to transfer the stickers to WhatsApp.\n"
                    "Links: [App Store](https://apps.apple.com/ru/app/sticker-maker-studio/id1443326857) "
                    "or [Google Play](https://play.google.com/store/apps/details?id=com.marsvard.stickermakerforwhatsapp)."
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except TimedOut:
            logger.error("Timed out while sending the zip file")

    await update.callback_query.edit_message_reply_markup(reply_markup=None)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""

    logger.error("Exception while handling an update:", exc_info=context.error)

    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
    )
    tb_string = "".join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        "An exception was raised while handling an update\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n"
        f"<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    if DEVELOPER_CHAT_ID:

        await context.bot.send_message(
            chat_id=DEVELOPER_CHAT_ID, text=message, parse_mode="HTML"
        )


app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start_command))

app.add_handler(MessageHandler(filters.TEXT, text_handler))

app.add_handler(MessageHandler(filters.Sticker.ALL, sticker_handler))

app.add_handler(MessageHandler(filters.PHOTO, photo_handler))

app.add_handler(MessageHandler(filters.ANIMATION, animation_handler))

app.add_handler(MessageHandler(filters.AUDIO, audio_handler))

app.add_handler(MessageHandler(filters.Document.ALL, document_handler))

app.add_handler(MessageHandler(filters.VIDEO, video_handler))

app.add_handler(MessageHandler(filters.VOICE, voice_handler))

app.add_handler(MessageHandler(filters.Dice.ALL, dice_handler))

app.add_handler(MessageHandler(filters.POLL, poll_handler))

app.add_handler(CallbackQueryHandler(info_btn, pattern="info"))

app.add_handler(CallbackQueryHandler(download_pack, pattern=r"^ds:\w+$"))


app.add_handler(InlineQueryHandler(inline_query))

app.add_error_handler(error_handler)

app.run_polling(allowed_updates=Update.ALL_TYPES)
