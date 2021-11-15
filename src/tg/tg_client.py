import logging

from datetime import datetime
from typing import List

from telethon import TelegramClient
from telethon.tl.types import User
from telethon.sessions import StringSession

from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)


class TgClient(Singleton):
    def __init__(self, tg_config=None):
        if self.was_initialized():
            return

        self._tg_config = tg_config
        self._update_from_config()
        logger.info('TgClient successfully initialized')

    def update_config(self, new_tg_config: dict):
        """To be called after config automatic update"""
        self._tg_config = new_tg_config
        self._update_from_config()

    def _update_from_config(self):
        self.api_client = TelegramClient(
            StringSession(self._tg_config['api_session']),
            self._tg_config['api_id'],
            self._tg_config['api_hash']
        )
        self.sysblok_chats = self._tg_config['sysblok_chats']
        self.channel = self._tg_config['channel']

    def _get_chat_users(self, chat_id: str) -> List[User]:
        with self.api_client:
            users = self.api_client.loop.run_until_complete(
                self.api_client.get_participants(chat_id)
            )
        return users

    def get_main_chat_users(self) -> List[User]:
        return self._get_chat_users(self.sysblok_chats['main_chat'])
