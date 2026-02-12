import asyncio
import logging
import os
import pickle
from collections import defaultdict
from typing import Callable

from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    PicklePersistence,
    filters,
)

from .app_context import AppContext
from .config_manager import ConfigManager
from .consts import (
    APP_SOURCE,
    COMMIT_HASH,
    COMMIT_URL,
    USAGE_LOG_LEVEL,
    CommandCategories,
    JobType,
    AccessLevel,
)
from .tg import handlers, sender, handler_strategies
from .tg.handler_registry import HANDLER_REGISTRY
from .tg.handlers.utils import direct_message_only

logging.addLevelName(USAGE_LOG_LEVEL, "NOTICE")


def usage(self, message, *args, **kws):
    self._log(USAGE_LOG_LEVEL, message, args, **kws)


logging.Logger.usage = usage
logger = logging.getLogger(__name__)


class SysBlokBot:
    """
    Main Bot class responsible for initialization and handler registration.

    Attributes:
        config_manager: Manages configuration settings.
        application: Telegram Application instance.
        telegram_sender: wrapper for sending messages.
        app_context: Application context state.
        handlers_info: Dictionary to store handler descriptions for /help command.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        signal_handler,
        skip_db_update: bool = False,
    ):
        self.config_manager = config_manager
        tg_config = config_manager.get_telegram_config()

        if (
            not os.path.exists("persistent_storage.pickle")
            or os.path.getsize("persistent_storage.pickle") == 0
        ):
            with open("persistent_storage.pickle", "wb") as f:
                pickle.dump(
                    {
                        "user_data": {},
                        "chat_data": {},
                        "bot_data": {},
                        "conversations": {},
                    },
                    f,
                )

        self.application = (
            ApplicationBuilder()
            .persistence(PicklePersistence(filepath="persistent_storage.pickle"))
            .token(tg_config["token"])
            # .post_shutdown(signal_handler)
            .concurrent_updates(True)
            .build()
        )
        self.telegram_sender = sender.TelegramSender(
            bot=self.application.bot, tg_config=tg_config
        )
        try:
            self.app_context = AppContext(config_manager, skip_db_update)
        except BaseException as e:
            # todo infra for such messages
            app_context_broken_msg = (
                f"[{APP_SOURCE}] Bot failed to initialise AppContext"
            )
            if COMMIT_HASH:
                app_context_broken_msg += (
                    f', revision <a href="{COMMIT_URL}">{COMMIT_HASH}</a>.'
                )
            app_context_broken_msg += f"\n{str(e)}"
            self.telegram_sender.send_error_log(app_context_broken_msg)
            raise
        self.handlers_info = defaultdict(lambda: defaultdict(dict))
        logger.info("SysBlokBot successfully initialized")

    def init_handlers(self):
        """
        Initializes all bot handlers from the central HANDLER_REGISTRY.
        Iterates over the registry, resolves handlers (direct or job-based),
        applies wrappers (e.g. direct_only), and registers them with the application.
        """
        # Strategy mapping
        strategies = {
            JobType.ADMIN_BROADCAST: handler_strategies.AdminBroadcastFactory(),
            JobType.ADMIN_REPLY: handler_strategies.AdminReplyFactory(),
            JobType.MANAGER_REPLY: handler_strategies.ManagerReplyFactory(),
            JobType.USER_REPLY: handler_strategies.UserReplyFactory(),
        }

        # Register handlers from registry
        for config in HANDLER_REGISTRY:
            # Resolve handler
            handler = config.handler_func

            if config.job_name:
                strategy = strategies.get(config.job_type)
                if strategy:
                    handler = strategy.create(
                        config.job_name,
                        self.app_context,
                        self.telegram_sender,
                        self.config_manager,
                    )
                else:
                    logger.error(
                        f"Unknown job type {config.job_type} for job {config.job_name}"
                    )
                    continue

            # Apply modifiers
            if config.direct_only:
                handler = direct_message_only(handler)

            # Register
            if config.access_level == AccessLevel.ADMIN:
                self.add_admin_handler(
                    config.command, config.category, handler, config.description
                )
            elif config.access_level == AccessLevel.MANAGER:
                self.add_manager_handler(
                    config.command, config.category, handler, config.description
                )
            elif config.access_level == AccessLevel.USER:
                self.add_user_handler(
                    config.command, config.category, handler, config.description
                )

        # Special case: Help handler (requires dynamic self.handlers_info)
        self.add_admin_handler(
            "help",
            CommandCategories.DEBUG,
            lambda update, context: handlers.help(update, context, self.handlers_info),
            "получить список доступных команд",
        )

        # on non-command user message

        def asyncify(func):
            async def wrapper(*args, **kwargs):
                results = func(*args, **kwargs)
                return results

            return wrapper

        self.application.add_handler(
            MessageHandler(filters.TEXT, asyncify(handlers.handle_user_message))
        )
        self.application.add_handler(
            CallbackQueryHandler(asyncify(handlers.handle_callback_query))
        )
        self.application.add_handler(
            MessageHandler(
                filters.StatusUpdate.NEW_CHAT_MEMBERS,
                asyncify(handlers.handle_new_members),
            )
        )

        # log all errors
        self.application.add_error_handler(asyncify(handlers.error))

    def run(self):
        # Start the Bot
        logger.info("Starting polling...")
        # TODO add non-blocking runtime (graceful termination for SIGTERM etc)
        self.application.run_polling()

    # Methods, adding command handlers and setting them to /help cmd for proper audience
    def add_handler(self, handler_cmd: str, handler_func: Callable):
        """Adds handler silently. Noone will see it in /help output"""

        def add_usage_logging(func):
            async def wrapper(*args, **kwargs):
                try:
                    update = args[0]
                    username = (
                        update.message.from_user.username or update.message.from_user.id
                    )
                    logger.usage(f"Handler {handler_cmd} was called by {username}...")
                except BaseException:
                    logger.usage(f"Handler {handler_cmd} was called...")

                # Check if func is async and await if necessary
                results = func(*args, **kwargs)
                if asyncio.iscoroutine(results):
                    results = await results

                logger.usage(f"Handler {handler_cmd} finished")
                return results

            return wrapper

        self.application.add_handler(
            CommandHandler(handler_cmd, add_usage_logging(handler_func))
        )

    def add_admin_handler(
        self,
        handler_cmd: str,
        handler_category: CommandCategories,
        handler_func: Callable,
        description: str = "",
    ):
        """
        Adds handler. It will be listed in /help for admins only
        Note: method does not automatically handle invokation restrictions.
        See tg.utils#admin_only
        """
        self.add_handler(handler_cmd, handler_func)
        self.handlers_info[handler_category]["admin"][f"/{handler_cmd}"] = description

    def add_manager_handler(
        self,
        handler_cmd: str,
        handler_category: CommandCategories,
        handler_func: Callable,
        description: str = "",
    ):
        """
        Adds handler. It will be listed in /help for admins and managers only
        Note: method does not automatically handle invokation restrictions.
        See tg.utils#manager_only
        """
        self.add_handler(handler_cmd, handler_func)
        self.handlers_info[handler_category]["manager"][f"/{handler_cmd}"] = description

    def add_user_handler(
        self,
        handler_cmd: str,
        handler_category: CommandCategories,
        handler_func: Callable,
        description: str = "",
    ):
        """Adds handler. It will be listed in /help for everybody"""
        self.add_handler(handler_cmd, handler_func)
        self.handlers_info[handler_category]["user"][f"/{handler_cmd}"] = description
