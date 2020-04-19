"""Sends messages"""

import logging

import telegram

logger = logging.getLogger(__name__)

class TelegramSender:
    def __init__(
            self,
            bot: telegram.Bot,
            tg_config: dict
    ):
        self.bot = bot
        self._tg_config = tg_config
        self._update_from_config()

    def send_to_manager(self, message_text: str):
        for manager_chat_id in self.manager_chat_ids:
            if not manager_chat_id:
                logger.error(f'Can\'t send message to manager, check config: \
                    manager_chat_id is {manager_chat_id}')
                continue
            self.send_to_chat_id(message_text, manager_chat_id)

    def send_to_chat_id(self, message_text: str, chat_id: int):
        try:
            self.bot.send_message(
                text=message_text,
                chat_id=chat_id,
                disable_notification=self.is_silent,
                parse_mode=telegram.ParseMode.HTML
            )
        except telegram.TelegramError as e:
            logger.error(f'Could not send a message: {e}')


    def update_config(self, new_tg_config):
        """
        To be called after config automatic update.
        Note: Does not support changing telegram api key.
        """
        self._tg_config = new_tg_config
        self._update_from_config()

    def _update_from_config(self):
        """Update attributes according to current self._tg_config"""
        self.manager_chat_ids = self._tg_config.get('_tmp_', {}).get('manager_chat_ids')
        self.is_silent = self._tg_config.get('is_silent', True)
