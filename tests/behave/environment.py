"""
Behave environment setup and teardown.
"""

import logging

from src.app_context import AppContext
from src.config_manager import ConfigManager
from src.db.db_client import DBClient

logger = logging.getLogger(__name__)


def before_all(context):
    """Run before all scenarios."""
    # Reset singletons to ensure clean state
    AppContext.drop_instance()
    ConfigManager.drop_instance()
    DBClient.drop_instance()
    logger.info("Behave test suite started")


def before_scenario(context, scenario):
    """Run before each scenario."""
    # Reset singletons for each scenario
    AppContext.drop_instance()
    ConfigManager.drop_instance()
    DBClient.drop_instance()

    # Initialize context variables
    context.config_manager = None
    context.app_context = None
    context.bot = None
    context.captured_messages = []
    context.user_id = None
    context.user_username = None
    context.is_admin = False

    logger.info(f"Starting scenario: {scenario.name}")


def after_scenario(context, scenario):
    """Run after each scenario."""
    # Clean up bot pickle file if it was created
    if hasattr(context, "bot") and hasattr(context.bot, "_test_pickle_path"):
        import os

        if os.path.exists(context.bot._test_pickle_path):
            os.remove(context.bot._test_pickle_path)
        # Clean up persistent_storage.pickle if we created it
        if (
            hasattr(context.bot, "_test_pickle_original")
            and not context.bot._test_pickle_original
        ):
            test_pickle = "persistent_storage.pickle"
            if os.path.exists(test_pickle):
                os.remove(test_pickle)

    # Clean up singletons
    AppContext.drop_instance()
    ConfigManager.drop_instance()
    DBClient.drop_instance()

    # Clear captured messages
    context.captured_messages = []

    logger.info(f"Finished scenario: {scenario.name}")


def after_all(context):
    """Run after all scenarios."""
    # Final cleanup
    AppContext.drop_instance()
    ConfigManager.drop_instance()
    DBClient.drop_instance()
    logger.info("Behave test suite finished")
