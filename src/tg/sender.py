"""Sends messages"""

import asyncio
import json
import logging
import re
import time
from typing import Callable, List

import nest_asyncio
import requests
import telegram

from ..app_context import AppContext
from ..consts import MESSAGE_DELAY_SEC
from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)


class TelegramSender(Singleton):
    def __init__(
        self,
        bot: telegram.Bot = None,
        tg_config: dict = None,
    ):
        if self.was_initialized():
            return
        if bot is None or tg_config is None:
            raise ValueError(
                "On first TelegramSender initialization bot and tg_config must be not None"
            )

        self.bot = bot
        self._tg_config = tg_config
        self._update_from_config()
        logger.info("TelegramSender successfully initialized")

    def create_reply_send(self, update: telegram.Update) -> Callable[[str], None]:
        """
        Returns a function send(message_text), making reply to user.
        """
        if not isinstance(update, telegram.Update):
            logger.warning(f"Should be telegram.Update, found: {update}")

        def sender(message):
            self.send_to_chat_id(message, update.message.chat_id)

        # add destination info
        sender.update = update
        return sender

    def create_chat_ids_send(self, chat_ids: List[int]) -> Callable[[str], None]:
        """
        Returns a function send(message_text), sending message to all chat_ids.
        """
        if isinstance(chat_ids, int):
            chat_ids = [chat_ids]

        def sender(message, **kwargs):
            self.send_to_chat_ids(message, chat_ids, **kwargs)

        # add destination info
        sender.chat_ids = chat_ids
        return sender

    def send_to_chat_ids(self, message_text: str, chat_ids: List[int]):
        """
        Sends a message to list of chat ids.
        """
        for chat_id in chat_ids:
            self.send_to_chat_id(message_text, chat_id)

    def send_to_chat_id(self, message_text: str, chat_id: int, **kwargs) -> bool:
        """
        Sends a message to a single chat_id.
        """
        if "poll_options" in kwargs:
            # Handle poll sending
            poll_options = kwargs["poll_options"]
            resp = requests.get(
                url=f"https://api.telegram.org/bot{self._tg_config['token']}/sendPoll",
                params={
                    "chat_id": chat_id,
                    "question": poll_options["question"],
                    "options": json.dumps(poll_options["options"]),
                    "is_anonymous": poll_options["is_anonymous"],
                },
            )
            resp.raise_for_status()
            return True
        if ".png" in message_text:
            for pict in re.findall(r"\S*\.png", message_text):
                self.bot.send_photo(
                    photo=open(pict, "rb"),
                    chat_id=chat_id,
                    disable_notification=self.is_silent,
                    **kwargs,
                )
            message_text = re.sub(r"\S*\.png", "", message_text)
        if message_text != "":
            try:
                loop = asyncio.get_event_loop()
                nest_asyncio.apply(loop)
                messages = paragraphs_to_messages([message_text.strip()])
                for i, message in enumerate(messages):
                    if i > 0:
                        time.sleep(MESSAGE_DELAY_SEC)
                    if message.startswith("<code>") and "</code>" not in message:
                        message = message + "</code>"
                    elif message.endswith("</code>") and "<code>" not in message:
                        message = "<code>" + message
                    payload = {
                        "text": message,
                        "chat_id": chat_id,
                        "silent": self.is_silent,
                        "no_webpage": self.disable_web_page_preview,
                        "parse_mode": "html",
                    }
                    if "reply_markup" in kwargs:
                        payload["reply_markup"] = kwargs["reply_markup"].to_json()
                    resp = requests.get(
                        url=f"https://api.telegram.org/bot{self._tg_config['token']}/sendMessage",
                        json=payload,
                    )
                    resp.raise_for_status()
                return True
            except telegram.error.TelegramError as e:
                logger.error(f"Could not send a message to {chat_id}", exc_info=e)
                loop = asyncio.get_event_loop()
                nest_asyncio.apply(loop)
                chat_name = AppContext().db_client.get_chat_name(chat_id)
                for error_logs_recipient in self.error_logs_recipients:
                    try:
                        # Try redirect unsended message to error_logs_recipients
                        loop.run_until_complete(
                            self.bot.send_message(
                                text=f"Unsended message to {chat_name} {chat_id}\n{message}"[
                                    : telegram.constants.MessageLimit.MAX_TEXT_LENGTH
                                ],
                                chat_id=error_logs_recipient,
                                disable_notification=self.is_silent,
                                disable_web_page_preview=self.disable_web_page_preview,
                                parse_mode=telegram.constants.ParseMode.HTML,
                                **kwargs,
                            )
                        )
                    except telegram.error.TelegramError as e:
                        logger.error(
                            "Could not redirect unsended message "
                            f"to error_logs_recipients {error_logs_recipient}",
                            exc_info=e,
                        )

                # HTML parse error isn't a separate class in Telegram
                # So we need to dig into the exception message
                if "Can't parse entities" in e.message:
                    try:
                        # Try sending the plain-text version
                        loop.run_until_complete(
                            self.bot.send_message(
                                text=f"Unsended message to {chat_name} {chat_id}\n{message}"[
                                    : telegram.constants.MessageLimit.MAX_TEXT_LENGTH
                                ],
                                chat_id=error_logs_recipient,
                                disable_notification=self.is_silent,
                                disable_web_page_preview=self.disable_web_page_preview,
                                **kwargs,
                            )
                        )
                        return True
                    except telegram.error.TelegramError as e:
                        logger.error(
                            f"Could not send a plain-text message to {chat_id}",
                            exc_info=e,
                        )
            return False

    def send_error_log(self, error_log: str):
        self.send_to_chat_ids(error_log, self.error_logs_recipients)

    def send_usage_log(self, usage_log: str):
        self.send_to_chat_ids(usage_log, self.usage_logs_recipients)

    def send_important_event(self, event_text: str):
        logger.info(f'Sending important event: "{event_text}"')
        self.send_to_chat_ids(event_text, self.important_events_recipients)

    def update_config(self, new_tg_config):
        """
        To be called after config automatic update.
        Note: Does not support changing telegram api key.
        """
        self._tg_config = new_tg_config
        self._update_from_config()

    def _update_from_config(self):
        """Update attributes according to current self._tg_config"""
        self.important_events_recipients = self._tg_config.get(
            "important_events_recipients"
        )
        self.error_logs_recipients = self._tg_config.get("error_logs_recipients")
        self.usage_logs_recipients = self._tg_config.get("usage_logs_recipients")
        self.is_silent = self._tg_config.get("is_silent", True)
        self.disable_web_page_preview = self._tg_config.get(
            "disable_web_page_preview", True
        )


def pretty_send(paragraphs: List[str], send: Callable[[str], None]) -> str:
    """
    Send a bunch of paragraphs grouped into messages with adequate delays.
    Return the whole message for testing purposes.
    """
    messages = paragraphs_to_messages(paragraphs)
    for i, message in enumerate(messages):
        if i > 0:
            time.sleep(MESSAGE_DELAY_SEC)
        if message.startswith("<code>") and "</code>" not in message:
            message = message + "</code>"
        elif message.endswith("</code>") and "<code>" not in message:
            message = "<code>" + message
        send(message)
    return "\n".join(messages)


def paragraphs_to_messages(
    paragraphs: List[str],
    char_limit=telegram.constants.MessageLimit.MAX_TEXT_LENGTH,
    delimiter="\n\n",
) -> List[str]:
    """
    Makes as few message texts as possible from given paragraph list.
    """
    if not paragraphs:
        logger.warning("No paragraphs to process, exiting")
        return []

    delimiter_len = len(delimiter)
    messages = []
    paragraphs_in_message = []
    char_counter = char_limit  # so that we start a new message immediately

    for paragraph in paragraphs:
        if len(paragraph) + char_counter + delimiter_len < char_limit:
            paragraphs_in_message.append(paragraph)
            char_counter += len(paragraph) + delimiter_len
        else:
            # Overflow, starting a new message
            messages.append(delimiter.join(paragraphs_in_message))
            # if paragraph is too long, force split it for line breaks
            while len(paragraph) >= char_limit:
                # last line break before limit
                last_break_index = paragraph[:char_limit].rfind("\n")
                if last_break_index == -1:
                    # if no line breaks, force split
                    last_break_index = char_limit - 1
                messages.append(paragraph[:last_break_index])
                paragraph = paragraph[last_break_index:].strip()
            # start new message
            paragraphs_in_message = [paragraph]
            char_counter = len(paragraph)
    # add last remaining message to the list
    messages.append(delimiter.join(paragraphs_in_message))

    # first message is empty by design.
    assert messages[0] == ""
    return messages[1:]
