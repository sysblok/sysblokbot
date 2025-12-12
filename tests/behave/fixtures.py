"""
Test fixtures and utilities for behave tests.
"""

import logging
import os
import pickle
import tempfile
from contextlib import contextmanager
from typing import List, Optional
from unittest.mock import MagicMock

import telegram

from src.bot import SysBlokBot
from src.config_manager import ConfigManager
from src.db.db_client import DBClient
from src.db.db_objects import Base

logger = logging.getLogger(__name__)


def create_test_config(
    admin_chat_ids: List = None, manager_chat_ids: List = None
) -> dict:
    """
    Create a minimal test configuration with all required keys.

    Args:
        admin_chat_ids: List of admin chat IDs/usernames
        manager_chat_ids: List of manager chat IDs/usernames

    Returns:
        Test configuration dictionary
    """
    admin_chat_ids = admin_chat_ids or []
    manager_chat_ids = manager_chat_ids or []

    return {
        "telegram": {
            "token": "test_token",
            "is_silent": False,
            "disable_web_page_preview": False,
            "admin_chat_ids": admin_chat_ids,
            "manager_chat_ids": manager_chat_ids,
            "important_events_recipients": [],
            "error_logs_recipients": [],
            "usage_logs_recipients": [],
        },
        "db": {"uri": "sqlite:///:memory:"},
        "strings": {"uri": "sqlite:///:memory:"},
        "sheets": {
            "api_key_path": "/tmp/test_key.json",
            "authors_sheet_key": "test_authors_key",
            "curators_sheet_key": "test_curators_key",
            "hr_sheet_key": "test_hr_key",
            "hr_pt_sheet_key": "test_hr_pt_key",
            "post_registry_sheet_key": "test_post_registry_key",
            "rubrics_registry_sheet_key": "test_rubrics_key",
            "strings_sheet_key": "test_strings_key",
        },
        "drive": {
            "api_key_path": "/tmp/test_key.json",
            "illustrations_folder_key": "test_folder_key",
        },
        "trello": {
            "api_key": "test_key",
            "token": "test_token",
            "board_id": "test_board_id",
            "deprecated": False,
        },
        "focalboard": {
            "url": "http://test.example.com",
            "token": "test_token",
            "board_id": "test_board_id",
        },
        "facebook": {
            "access_token": "test_token",
            "page_id": "test_page_id",
        },
        "n8n": {
            "webhook_url": "http://test.example.com/webhook",
        },
    }


def create_test_config_manager(config: dict = None) -> ConfigManager:
    """
    Create a test ConfigManager with the given config.

    Args:
        config: Configuration dictionary (uses default if None)

    Returns:
        ConfigManager instance
    """
    if config is None:
        config = create_test_config()

    config_manager = ConfigManager()
    config_manager._latest_config = config
    config_manager._latest_config_ts = None
    return config_manager


def setup_test_database(config_manager: ConfigManager) -> DBClient:
    """
    Set up a fresh in-memory test database.

    Args:
        config_manager: ConfigManager instance

    Returns:
        DBClient instance
    """
    db_config = config_manager.get_db_config()
    db_client = DBClient(db_config=db_config)

    # Create all tables
    Base.metadata.create_all(db_client.engine)

    return db_client


def create_mock_update(
    user_id: int,
    username: Optional[str] = None,
    chat_id: Optional[int] = None,
    text: str = "/command",
) -> telegram.Update:
    """
    Create a mock Telegram Update object.

    Args:
        user_id: Telegram user ID
        username: Telegram username (optional)
        chat_id: Chat ID (defaults to user_id for DM)
        text: Message text

    Returns:
        Mock telegram.Update object
    """
    if chat_id is None:
        chat_id = user_id

    # Create mock user
    mock_user = MagicMock(spec=telegram.User)
    mock_user.id = user_id
    mock_user.username = username
    mock_user.first_name = "Test"
    mock_user.last_name = "User"
    mock_user.is_bot = False

    # Create mock chat
    mock_chat = MagicMock(spec=telegram.Chat)
    mock_chat.id = chat_id
    mock_chat.type = "private" if chat_id == user_id else "group"
    mock_chat.title = None

    # Create mock message
    mock_message = MagicMock(spec=telegram.Message)
    mock_message.message_id = 1
    mock_message.from_user = mock_user
    mock_message.chat = mock_chat
    mock_message.chat_id = chat_id
    mock_message.text = text
    mock_message.date = None

    # Create mock update
    mock_update = MagicMock(spec=telegram.Update)
    mock_update.update_id = 1
    mock_update.message = mock_message
    mock_update.callback_query = None

    return mock_update


def create_mock_context() -> MagicMock:
    """
    Create a mock CallbackContext object.

    Returns:
        Mock CallbackContext
    """
    mock_context = MagicMock()
    mock_context.chat_data = {}
    mock_context.user_data = {}
    mock_context.bot_data = {}
    return mock_context


def create_test_bot(
    config_manager: ConfigManager, skip_db_update: bool = True
) -> SysBlokBot:
    """
    Create a test bot instance without polling.

    Args:
        config_manager: ConfigManager instance
        skip_db_update: Whether to skip DB updates during initialization

    Returns:
        SysBlokBot instance
    """
    # Create a temporary pickle file for persistence
    temp_pickle = tempfile.NamedTemporaryFile(delete=False, suffix=".pickle")
    temp_pickle_path = temp_pickle.name
    temp_pickle.close()

    # Initialize pickle file with empty data
    with open(temp_pickle_path, "wb") as f:
        pickle.dump(
            {
                "user_data": {},
                "chat_data": {},
                "bot_data": {},
                "conversations": {},
            },
            f,
        )

    # Create mock signal handler
    signal_handler = MagicMock()

    # Temporarily create the pickle file in current directory for bot initialization
    test_pickle_path = "persistent_storage.pickle"
    original_exists = os.path.exists(test_pickle_path)

    # Copy temp pickle to expected location
    import shutil

    shutil.copy(temp_pickle_path, test_pickle_path)

    try:
        # Create bot
        bot = SysBlokBot(
            config_manager=config_manager,
            signal_handler=signal_handler,
            skip_db_update=skip_db_update,
        )

        # Initialize handlers
        bot.init_handlers()

        # Store pickle path for cleanup
        bot._test_pickle_path = temp_pickle_path
        bot._test_pickle_original = original_exists

        return bot
    except Exception:
        # Clean up on error
        if os.path.exists(test_pickle_path) and not original_exists:
            os.remove(test_pickle_path)
        if os.path.exists(temp_pickle_path):
            os.remove(temp_pickle_path)
        raise


@contextmanager
def capture_send_messages(context):
    """
    Context manager to capture messages sent by the bot.

    Usage:
        with capture_send_messages(context):
            # call handler
            pass
        # Check context.captured_messages
    """
    # Get the TelegramSender singleton instance
    sender_instance = context.bot.telegram_sender

    # Store original methods
    original_send_to_chat_id = sender_instance.send_to_chat_id
    original_create_reply_send = sender_instance.create_reply_send

    def patched_send_to_chat_id(message_text: str, chat_id: int, **kwargs):
        """Capture messages instead of sending them."""
        context.captured_messages.append(
            {
                "message": message_text,
                "chat_id": chat_id,
                "kwargs": kwargs,
            }
        )
        logger.debug(f"Captured message: {message_text}")
        return True  # Return success to avoid error handling

    def patched_create_reply_send(self, update):
        """Create a send function that uses the patched send_to_chat_id."""

        def sender(message):
            # Always use the current patched method
            patched_send_to_chat_id(message, update.message.chat_id)

        sender.update = update
        return sender

    # Replace both methods on the instance
    import types

    sender_instance.send_to_chat_id = types.MethodType(
        patched_send_to_chat_id, sender_instance
    )
    sender_instance.create_reply_send = types.MethodType(
        patched_create_reply_send, sender_instance
    )

    try:
        yield
    finally:
        # Restore original methods
        sender_instance.send_to_chat_id = original_send_to_chat_id
        sender_instance.create_reply_send = original_create_reply_send
