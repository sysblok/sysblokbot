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
)
from .jobs.utils import get_job_runnable
from .tg import handlers, sender
from .tg.handler_registry import HANDLER_REGISTRY
from .tg.handlers.utils import admin_only, direct_message_only, manager_only

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
        Initializes Telegram handlers based on the configuration in `HANDLER_REGISTRY`.
        Iterates over the registry, resolves handlers (direct or job-based),
        applies wrappers (e.g. direct_only), and registers them with the application.
        """
        # Register handlers from registry
        for config in HANDLER_REGISTRY:
            # Resolve handler
            handler = config.handler_func
            if config.job_name:
                if config.job_type == "admin_broadcast":
                    handler = self.admin_broadcast_handler(config.job_name)
                elif config.job_type == "admin_reply":
                    handler = self.admin_reply_handler(config.job_name)
                elif config.job_type == "manager_reply":
                    handler = self.manager_reply_handler(config.job_name)
                elif config.job_type == "user_reply":
                    handler = self.user_handler(config.job_name)

            # Apply modifiers
            if config.direct_only:
                handler = direct_message_only(handler)

            # Register
            if config.access_level == "admin":
                self.add_admin_handler(
                    config.command, config.category, handler, config.description
                )
            elif config.access_level == "manager":
                self.add_manager_handler(
                    config.command, config.category, handler, config.description
                )
            elif config.access_level == "user":
                self.add_user_handler(
                    config.command, config.category, handler, config.description
                )
            else:  # hidden
                self.add_handler(config.command, handler)

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
                if asyncio.iscoroutine(results):
                    return await results
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

    # Methods, creating handlers from jobs with proper invocation restrictions
    def admin_broadcast_handler(self, job_name: str) -> Callable:
        """
        Handler that invokes the job as configured in settings, if called by admin.
        Can possibly send message to multiple chat ids, if configured in settings.
        """
        return admin_only(self._create_broadcast_handler(job_name))

    def admin_reply_handler(self, job_name: str) -> Callable:
        """
        Handler that invokes the job as configured in settings, if called by admin.
        Replies to the admin that invoked it.
        """
        return admin_only(self._create_reply_handler(job_name))

    def manager_reply_handler(self, job_name: str) -> Callable:
        """
        Handler that replies if manager invokes it (DM or chat).
        """
        return manager_only(
            self._create_reply_handler(
                job_name,
            )
        )

    def user_handler(self, job_name: str) -> Callable:
        """
        Handler that replies to any user.
        """
        return self._create_reply_handler(job_name)

    def _create_reply_handler(self, job_name: str) -> Callable:
        """
        Creates a handler that replies to a message of given user.
        """
        return lambda update, tg_context: get_job_runnable(job_name)(
            app_context=self.app_context,
            send=self.telegram_sender.create_reply_send(update),
            called_from_handler=True,
            args=update.message.text.split()[1:],
        )

    def _create_broadcast_handler(self, job_name: str) -> Callable:
        """
        Creates a handler that sends message to list of chat ids.
        """
        chat_ids = self.config_manager.get_job_send_to(job_name)
        return lambda update, tg_context: get_job_runnable(job_name)(
            app_context=self.app_context,
            send=self.telegram_sender.create_chat_ids_send(chat_ids),
            called_from_handler=True,
        )
