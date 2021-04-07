import logging
from typing import List, Iterable

from datetime import datetime

from telethon.sessions import StringSession

from ..consts import ReportPeriod
from ..utils.singleton import Singleton
from telethon import TelegramClient

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
        self.channel = self._tg_config['channel']
