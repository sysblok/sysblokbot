"""Sends messages"""

import logging

import telegram

logger = logging.getLogger(__name__)

class TelegramSender:
    def __init__(
            self,
            bot: telegram.Bot,
            chats_config: dict,
            is_silent: bool
    ):
        self.bot = bot
        self.chats_config = chats_config
        self.is_silent = is_silent

    def send_to_manager(self, message_text: str):
        manager_chat_id = self.chats_config.get('manager_chat_id')
        if not manager_chat_id:
            logger.error(f'Can\'t send message to manager, check config: \
                manager_chat_id is {manager_chat_id}')
            return
        self.send_to_chat_id(message_text, manager_chat_id)

    def send_to_chat_id(self, message_text: str, chat_id: int):
        try:
            self.bot.send_message(
                text=message_text,
                chat_id=chat_id,
                disable_notification=self.is_silent
            )
        except telegram.TelegramError as e:
            logger.error(f'Could not send a message: {e}')
