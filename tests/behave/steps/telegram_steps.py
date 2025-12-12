"""
Step definitions for shrug command tests.
"""

import asyncio
import logging
from unittest.mock import MagicMock

from behave import given, then, when

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.app_context import AppContext  # noqa: E402

# Import fixtures - use direct import after path is set
import importlib.util  # noqa: E402

fixtures_path = Path(__file__).parent.parent / "fixtures.py"
spec = importlib.util.spec_from_file_location("fixtures", fixtures_path)
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)

# Import functions from fixtures
capture_send_messages = fixtures.capture_send_messages
create_mock_context = fixtures.create_mock_context
create_mock_update = fixtures.create_mock_update
create_test_bot = fixtures.create_test_bot
create_test_config = fixtures.create_test_config
create_test_config_manager = fixtures.create_test_config_manager
setup_test_database = fixtures.setup_test_database

logger = logging.getLogger(__name__)


@given("a user with telegram user id {user_id:d}")
def step_given_user_with_telegram_id(context, user_id):
    """Set the user ID for the test."""
    context.user_id = user_id
    context.user_username = None
    logger.info(f"Set user ID: {user_id}")


@given("the user is an admin")
def step_given_user_is_admin(context):
    """Mark the user as an admin."""
    context.is_admin = True
    logger.info(f"User {context.user_id} is marked as admin")


@given("the user is not an admin")
def step_given_user_is_not_admin(context):
    """Mark the user as not an admin."""
    context.is_admin = False
    logger.info(f"User {context.user_id} is marked as non-admin")


@given("bot is initialized")
def step_given_bot_initialized(context):
    """Initialize the bot with test configuration."""
    from unittest.mock import patch, MagicMock
    from src.sheets.sheets_client import GoogleSheetsClient
    from src.drive.drive_client import GoogleDriveClient
    from src.trello.trello_client import TrelloClient
    from src.focalboard.focalboard_client import FocalboardClient
    from src.tg.tg_client import TgClient

    # Determine admin_chat_ids based on whether user is admin
    admin_chat_ids = []
    if context.is_admin:
        # Add user ID to admin_chat_ids
        admin_chat_ids = [context.user_id]
        if context.user_username:
            admin_chat_ids.append(context.user_username)

    # Create test config
    test_config = create_test_config(admin_chat_ids=admin_chat_ids)
    context.config_manager = create_test_config_manager(test_config)

    # Set up test database
    context.db_client = setup_test_database(context.config_manager)

    # Mock client authorization methods to avoid external API calls
    def mock_trello_update(self):
        """Mock TrelloClient._update_from_config to avoid API calls."""
        self.api_key = self._trello_config["api_key"]
        self.token = self._trello_config["token"]
        self.board_id = self._trello_config["board_id"]
        self.deprecated = self._trello_config.get("deprecated", False)
        self.default_payload = {
            "key": self.api_key,
            "token": self.token,
        }
        self.lists_config = {}
        self.custom_fields_type_config = {}
        self.custom_fields_config = {}

    def mock_focalboard_update(self):
        """Mock FocalboardClient._update_from_config to avoid HTTP calls."""
        self.token = self._focalboard_config["token"]
        self.url = self._focalboard_config["url"]
        self.board_id = self._focalboard_config["board_id"]
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.token}",
        }

    def mock_tg_update(self):
        """Mock TgClient._update_from_config to avoid Telegram client initialization."""
        # Create a mock TelegramClient instead of real one
        self.api_client = MagicMock()

    with (
        patch.object(GoogleSheetsClient, "_authorize", return_value=None),
        patch.object(GoogleDriveClient, "_authorize", return_value=None),
        patch.object(TrelloClient, "get_lists", return_value=[]),
        patch.object(TrelloClient, "get_board_custom_field_types", return_value=[]),
        patch.object(TrelloClient, "_update_from_config", mock_trello_update),
        patch.object(FocalboardClient, "_update_from_config", mock_focalboard_update),
        patch.object(TgClient, "_update_from_config", mock_tg_update),
    ):
        # Create app context (skip DB update to avoid external dependencies)
        context.app_context = AppContext(
            config_manager=context.config_manager,
            skip_db_update=True,
        )

    # Create test bot
    context.bot = create_test_bot(
        config_manager=context.config_manager,
        skip_db_update=True,
    )

    logger.info("Bot initialized")


@when('the user calls "{command}"')
def step_when_user_calls_command(context, command):
    """Simulate the user calling a command."""
    # Create mock update
    mock_update = create_mock_update(
        user_id=context.user_id,
        username=context.user_username,
        text=command,
    )

    # Capture messages
    with capture_send_messages(context):
        # Find and call the handler directly (avoiding Application initialization)
        command_name = command.lstrip("/")

        # Find the handler for this command
        handler_func = None
        for handler_group in context.bot.application.handlers[0]:
            if (
                hasattr(handler_group, "commands")
                and command_name in handler_group.commands
            ):
                handler_func = handler_group.callback
                break

        if handler_func is None:
            raise ValueError(f"Handler for command '{command_name}' not found")

        # Create mock context (CallbackContext doesn't allow direct assignment)
        mock_context = MagicMock()
        mock_context.chat_data = {}
        mock_context.user_data = {}
        mock_context.bot_data = {}

        # Call the handler
        try:
            # Create a new event loop for this test
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Call handler (may be async or sync)
            if asyncio.iscoroutinefunction(handler_func):
                loop.run_until_complete(handler_func(mock_update, mock_context))
            else:
                handler_func(mock_update, mock_context)
        except Exception as e:
            # Some errors are expected (like access denied)
            # The admin_only decorator will prevent execution and log a warning
            logger.warning(f"Handler execution exception: {e}")
            # Log the exception for debugging
            import traceback

            logger.warning(f"Exception traceback: {traceback.format_exc()}")

    logger.info(
        f"User called command: {command}, captured {len(context.captured_messages)} messages"
    )
    if len(context.captured_messages) == 0:
        logger.warning(
            f"No messages captured. User ID: {context.user_id}, Admin: {context.is_admin}"
        )
        logger.warning(
            f"Admin chat IDs in config: {context.app_context.admin_chat_ids}"
        )
        logger.warning(
            f"User ID in admin chat IDs: {context.user_id in context.app_context.admin_chat_ids}"
        )


@then('the bot replies with "{expected_message}"')
def step_then_bot_replies_with(context, expected_message):
    """Verify the bot replied with the expected message."""
    assert len(context.captured_messages) > 0, "Bot did not send any messages"

    # Check if any captured message contains the expected text
    # Normalize both strings by removing backslashes for comparison (handles escaping differences)
    expected_normalized = expected_message.replace("\\", "")
    found = False
    actual_messages = []
    for msg in context.captured_messages:
        message_text = msg["message"]
        actual_messages.append(message_text)
        message_normalized = message_text.replace("\\", "")
        # Check if expected message is in the actual message (normalized)
        if (
            expected_normalized in message_normalized
            or expected_message in message_text
        ):
            found = True
            break
        # Also check if they're equal (in case of exact match)
        if (
            message_text == expected_message
            or message_normalized == expected_normalized
        ):
            found = True
            break

    assert found, (
        f"Expected bot to reply with '{expected_message}', but got: {actual_messages}"
    )
    logger.info(f"Bot replied with expected message: {expected_message}")


@then("the bot doesn't reply")
def step_then_bot_doesnt_reply(context):
    """Verify the bot did not send any messages."""
    assert len(context.captured_messages) == 0, (
        f"Expected bot not to reply, but got: "
        f"{[m['message'] for m in context.captured_messages]}"
    )
    logger.info("Bot correctly did not reply")
