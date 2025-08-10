import logging
from typing import List, Tuple

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
