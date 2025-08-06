import html
import json
import logging
import traceback
from datetime import timedelta
from typing import List, Tuple
from uuid import uuid4

from decouple import config
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.constants import ChatType, MessageOriginType
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


BOT_TOKEN = config("BOT_TOKEN")
DEVELOPER_CHAT_ID = config("DEVELOPER_CHAT_ID", default=None)


def file_size(_bytes):

    logger.info("File size in bytes %s", _bytes)

    system = [
        (1.126e15, " PB"),
        (1.1e12, " TB"),
        (1.074e9, " GB"),
        (1.049e6, " MB"),
        (1024, " KB"),
        (1, (" byte", " bytes")),
    ]

    for factor, suffix in system:
        if _bytes >= factor:
            break

    amount = round(_bytes / factor, 1)

    if isinstance(suffix, tuple):
        singular, multiple = suffix

        if amount == 1:
            suffix = singular
        else:
            suffix = multiple

    return str(amount) + suffix


def text_html(contents: List[Tuple]):
    """
    Example:
        ```python
         text_html([("Name", "Raul"),("Username", "@raulcobiellas")])
        ```
    """

    message = []
    for index, row in enumerate(contents, start=1):
        header, content = row

        content = f"<code>{content}</code>" if content else ""

        if index == 1:
            message.append(f"<b>{header}</b>: {content}")

        elif index == len(contents):
            message.append(f"<b> └ {header}</b>: {content}")

        else:
            message.append(f"<b> ├ {header}</b>: {content}")

    return "\n".join(message)


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
                    InlineKeyboardButton(text="Your info", switch_inline_query="i"),
                    InlineKeyboardButton(text="ℹ", callback_data="info"),
                ]
            ]
        ),
    )


async def info_btn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    await update.callback_query.edit_message_text(
        text=(
            "<b>ℹ️Information:</b>\n\n"
            '👨‍💻Creator: <a href="https://github.com/raulodev">raulodev</a>\n'
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

    logger.info("Sticker: %s", update.message.sticker)

    text = text_html(
        [
            ("🎨Sticker ID", update.message.sticker.file_id),
            ("Emoji", update.message.sticker.emoji),
            ("Set Name", update.message.sticker.set_name),
            ("Link Set", f"https://t.me/addstickers/{update.message.sticker.set_name}"),
            ("Size", file_size(update.message.sticker.file_size)),
        ]
    )

    await update.message.reply_text(
        text=f"{forwarded_info}\n\n{text}" if forwarded_info else text,
        parse_mode="HTML",
    )


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

app.add_handler(InlineQueryHandler(inline_query))

app.add_error_handler(error_handler)

app.run_polling(allowed_updates=Update.ALL_TYPES)
