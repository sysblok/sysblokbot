import asyncio
import logging
from typing import Optional, Tuple

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User

from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SEC = 10
ENTITY_TIMEOUT_SEC = 10
STATS_TIMEOUT_SEC = 15
MESSAGES_TIMEOUT_SEC = 15
DISCONNECT_TIMEOUT_SEC = 10

# Outer bridge timeouts (see run_coroutine_threadsafe calls below) are kept above
# the sum of the inner per-call timeouts they wrap, so a legitimate worst-case
# run doesn't spuriously trip the outer bound right as the inner one would have
# reported the real failure.
RESOLVE_USERNAME_BRIDGE_TIMEOUT_SEC = 40
CHANNEL_STATS_BRIDGE_TIMEOUT_SEC = 90


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
            # We connect/disconnect explicitly around each short-lived
            # operation below rather than holding one persistent connection,
            # so we don't need (or want) Telethon's own background
            # auto-reconnect: it spawns its own reconnect task on connection
            # errors, independent of our connect()/disconnect() calls, and can
            # race with an explicit disconnect() happening around the same
            # time (Telethon's own source acknowledges this is unresolved -
            # see the TODO in MTProtoSender._start_reconnect).
            auto_reconnect=False,
        )
        self.sysblok_chats = self._tg_config["sysblok_chats"]
        self.channel = self._tg_config["channel"]

    def _run_coro(self, coro, timeout: float):
        """
        Bridges a coroutine onto self.api_client.loop.

        If that loop is already running (the normal case: called from a
        handler/scheduler thread while PTB is polling on its own loop in the
        main thread), schedules it via the thread-safe run_coroutine_threadsafe
        and blocks the calling thread for the result. If the loop isn't
        running yet (e.g. called during startup, before run_polling() has
        started it), we're on the same thread that owns the loop and nothing
        else is driving it, so run it directly instead of scheduling work onto
        a loop nobody is pumping - that would deadlock.
        """
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is self.api_client.loop:
            # Called synchronously from code already executing on this exact
            # loop's thread - blocking here would deadlock the same way a
            # foreign-thread call would if nothing pumped the loop, except
            # here it's this very callback that would need to. Unlike sender.py
            # this method's return value is actually consumed by callers, so
            # there's no safe fire-and-forget fallback - fail loudly instead of
            # silently returning a result callers can't use.
            raise RuntimeError(
                "TgClient method called reentrantly from its own event loop's "
                "thread - this would deadlock if we waited for a result."
            )

        if self.api_client.loop.is_running():
            future = asyncio.run_coroutine_threadsafe(coro, self.api_client.loop)
            return future.result(timeout=timeout)
        return self.api_client.loop.run_until_complete(coro)

    def resolve_telegram_username(self, username: str) -> Optional[Tuple[int, str]]:
        """
        Resolve Telegram username to user ID using telethon.

        Args:
            username: Telegram username (with or without @)

        Returns:
            Tuple of (user_id, username_without_@) or None if not found
        """
        try:
            return self._run_coro(
                self._resolve_telegram_username_async(username),
                timeout=RESOLVE_USERNAME_BRIDGE_TIMEOUT_SEC,
            )
        except Exception as e:
            logger.warning(f"Failed to resolve username {username}: {e}", exc_info=True)
            return None

    async def _resolve_telegram_username_async(
        self, username: str
    ) -> Optional[Tuple[int, str]]:
        normalized = username.lstrip("@")
        try:
            # Check if client is already connected
            was_connected = self.api_client.is_connected()

            if not was_connected:
                # Connect if not already connected
                await asyncio.wait_for(
                    self.api_client.connect(), timeout=CONNECT_TIMEOUT_SEC
                )

            try:
                entity = await asyncio.wait_for(
                    self.api_client.get_entity(normalized), timeout=ENTITY_TIMEOUT_SEC
                )

                # Only process User entities, skip channels, groups, bots, etc.
                if entity and isinstance(entity, User):
                    # Return username WITHOUT @ (as stored in DB)
                    return (entity.id, entity.username if entity.username else None)
                elif entity:
                    # Entity is not a User (could be Channel, Chat, Bot, etc.)
                    entity_type = type(entity).__name__
                    logger.info(
                        f"Username {username} resolved to {entity_type} "
                        "(not a User) - skipping"
                    )
                    return None
            finally:
                # Only disconnect if we connected it
                if not was_connected:
                    await asyncio.wait_for(
                        self.api_client.disconnect(), timeout=DISCONNECT_TIMEOUT_SEC
                    )
        except Exception as e:
            logger.warning(f"Failed to resolve username {username}: {e}", exc_info=True)
            return None

        return None

    def get_channel_stats(self, channel: str) -> Tuple:
        """
        Connects, fetches channel stats/entity/recent-message info, and
        disconnects, all in one session.

        Returns:
            Tuple of (stats, entity, messages)
        """
        return self._run_coro(
            self._get_channel_stats_async(channel),
            timeout=CHANNEL_STATS_BRIDGE_TIMEOUT_SEC,
        )

    async def _get_channel_stats_async(self, channel: str) -> Tuple:
        await asyncio.wait_for(self.api_client.connect(), timeout=CONNECT_TIMEOUT_SEC)
        try:
            stats = await asyncio.wait_for(
                self.api_client.get_stats(channel), timeout=STATS_TIMEOUT_SEC
            )
            entity = await asyncio.wait_for(
                self.api_client.get_entity(channel), timeout=ENTITY_TIMEOUT_SEC
            )
            messages = await asyncio.wait_for(
                self.api_client.get_messages(
                    channel,
                    ids=[
                        message_stats.msg_id
                        for message_stats in stats.recent_message_interactions
                    ],
                ),
                timeout=MESSAGES_TIMEOUT_SEC,
            )
            return stats, entity, messages
        finally:
            await asyncio.wait_for(
                self.api_client.disconnect(), timeout=DISCONNECT_TIMEOUT_SEC
            )
