import io
import logging
import zipfile
from itertools import islice
from typing import List, Tuple

from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


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

        elif content:

            if index == len(contents):
                message.append(f"<b> └ {header}</b>: {content}")

            else:
                message.append(f"<b> ├ {header}</b>: {content}")

    return "\n".join(message)


async def create_zip(
    set_name: str, part: int, title: str, bot_username: str, stickers: List[dict]
):

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("author.txt", f"@{bot_username}")
        zf.writestr("title.txt", f"{title} - ({part})")
        for sticker in stickers:
            sticker_file = sticker["file"]
            sticker_filename = sticker["filename"]

            sticker_file.seek(0)
            zf.writestr(sticker_filename, sticker_file.read())

    zip_buffer.seek(0)
    zip_buffer.name = f"{set_name}.part{part}.wastickers"
    return zip_buffer


def chunks(iterable, tam=30):
    it = iter(iterable)
    while True:
        bloque = list(islice(it, tam))
        if not bloque:
            break
        yield bloque


async def make_thumbnail(byte_array, size=(96, 96)):

    try:

        image = Image.open(io.BytesIO(byte_array))
        image.thumbnail(size)

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer

    except UnidentifiedImageError:
        logger.info("Len byte array: %s", len(byte_array))
        logger.info("Type byte array: %s", type(byte_array))

        logger.error("Error while making the thumbnail")
        with open("invalid_image_dump.png", "wb") as f:
            f.write(byte_array)


async def resize_image(byte_array, size=(512, 512)):

    try:

        image = Image.open(io.BytesIO(byte_array))

        resized_image = image.resize(size)

        buffer = io.BytesIO()
        resized_image.save(buffer, format="PNG")
        buffer.seek(0)

        return buffer

    except UnidentifiedImageError:

        logger.info("Len byte array: %s", len(byte_array))
        logger.info("Type byte array: %s", type(byte_array))

        logger.error("Error while resizing the image")
        with open("invalid_image_dump.png", "wb") as f:
            f.write(byte_array)
