import threading
import logging
from typing import List, Iterable

from datetime import datetime

from telegram.ext.dispatcher import run_async
from telethon import TelegramClient
from telethon.sessions import StringSession

from ..consts import ReportPeriod
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

    async def _get_chat_users(self, results):
        await self.api_client.connect()
        results.append([user.first_name for user in await self.api_client.get_participants(self.sysblok_chats['main_chat'])])

    def get_chat_users(self):
        results = []
        x = threading.Thread(target=self._get_chat_users, args=(results,))
        x.start()
        x.join()
        return str(results)

    # def get_chat_users(self):
    #     promise = self._get_chat_users()
    #     promise.run()
    #     return promise.result()