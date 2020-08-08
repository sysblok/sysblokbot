"""Sends messages"""

import logging
from typing import Callable, List

import telegram

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
                'On first TelegramSender initialization bot and tg_config must be not None'
            )

        self.bot = bot
        self._tg_config = tg_config
        self._update_from_config()
        logger.info('TelegramSender successfully initialized')

    def create_reply_send(
            self, update: telegram.Update
    ) -> Callable[[str], None]:
        """
        Returns a function send(message_text), making reply to user.
        """
        if not isinstance(update, telegram.Update):
            logger.warning(f'Should be telegram.Update, found: {update}')
        return lambda message: self.send_to_chat_id(
            message, update.message.chat_id
        )

    def create_chat_ids_send(
            self, chat_ids: List[int]
    ) -> Callable[[str], None]:
        """
        Returns a function send(message_text), sending message to all chat_ids.
        """
        if isinstance(chat_ids, int):
            chat_ids = [chat_ids]
        return lambda message: self.send_to_chat_ids(message, chat_ids)

    def send_to_chat_ids(self, message_text: str, chat_ids: List[int]):
        """
        Sends a message to list of chat ids.
        """
        for chat_id in chat_ids:
            self.send_to_chat_id(message_text, chat_id)

    def send_to_chat_id(self, message_text: str, chat_id: int, **kwargs):
        """
        Sends a message to a single chat_id.
        """
        try:
            self.bot.send_message(
                text=message_text.strip(),
                chat_id=chat_id,
                disable_notification=self.is_silent,
                disable_web_page_preview=self.disable_web_page_preview,
                parse_mode=telegram.ParseMode.HTML,
                **kwargs
            )
        except telegram.TelegramError as e:
            logger.error(f'Could not send a message: {e}')

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
            'important_events_recipients'
        )
        self.error_logs_recipients = self._tg_config.get(
            'error_logs_recipients'
        )
        self.usage_logs_recipients = self._tg_config.get(
            'usage_logs_recipients'
        )
        self.is_silent = self._tg_config.get('is_silent', True)
        self.disable_web_page_preview = self._tg_config.get('disable_web_page_preview', True)
