import logging
from typing import List, Optional, Tuple

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User

from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)


class TgClient(Singleton):
    def __init__(self, tg_config=None):
        if self.was_initialized():
            return

        self._tg_config = tg_config
        self._update_from_config()
        logger.info("TgClient successfully initialized")

    def update_config(self, new_tg_config: dict):
        """To be called after config automatic update"""
        self._tg_config = new_tg_config
        self._update_from_config()

    def _update_from_config(self):
        self.api_client = TelegramClient(
            StringSession(self._tg_config["api_session"]),
            self._tg_config["api_id"],
            self._tg_config["api_hash"],
        )
        # we need this to properly reauth in case the tokens need to be updated
        # we need "with" to open and close the event loop
        # removed as part of v20.0 migration
        # with self.api_client as client:
        #     client(functions.auth.ResetAuthorizationsRequest())
        self.sysblok_chats = self._tg_config["sysblok_chats"]
        self.channel = self._tg_config["channel"]

    def _get_chat_users(self, chat_id: str) -> List[User]:
        with self.api_client:
            users = self.api_client.loop.run_until_complete(
                self.api_client.get_participants(chat_id)
            )
        return users

    def get_main_chat_users(self) -> List[User]:
        return self._get_chat_users(self.sysblok_chats["main_chat"])

    def resolve_telegram_username(self, username: str) -> Optional[Tuple[int, str]]:
        """
        Resolve Telegram username to user ID using telethon.

        Args:
            username: Telegram username (with or without @)

        Returns:
            Tuple of (user_id, username_without_@) or None if not found
        """
        # Normalize: remove @ for telethon API
        normalized = username.lstrip("@")

        try:
            # Check if client is already connected
            was_connected = self.api_client.is_connected()

            if not was_connected:
                # Connect if not already connected
                self.api_client.loop.run_until_complete(self.api_client.connect())

            try:
                entity = self.api_client.loop.run_until_complete(
                    self.api_client.get_entity(normalized)
                )

                # Only process User entities, skip channels, groups, bots, etc.
                if entity and isinstance(entity, User):
                    # Return username WITHOUT @ (as stored in DB)
                    return (entity.id, entity.username if entity.username else None)
                elif entity:
                    # Entity is not a User (could be Channel, Chat, Bot, etc.)
                    entity_type = type(entity).__name__
                    logger.info(
                        f"Username {username} resolved to {entity_type} (not a User) - skipping"
                    )
                    return None
            finally:
                # Only disconnect if we connected it
                if not was_connected:
                    self.api_client.disconnect()
        except Exception as e:
            logger.warning(f"Failed to resolve username {username}: {e}", exc_info=True)
            return None

        return None
