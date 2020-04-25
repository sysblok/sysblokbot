import logging
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from .tg import handlers
from .app_context import AppContext
from .config_manager import ConfigManager


logger = logging.getLogger(__name__)


class SysBlokBot:
    def __init__(self, config_manager: ConfigManager, signal_handler):
        self.updater = Updater(
            config_manager.get_latest_config()['telegram']['token'],
            use_context=True,
            user_sig_handler=signal_handler,
        )
        self.dp = self.updater.dispatcher
        self.app_context = AppContext(config_manager)

    def init_handlers(self):
        # all command handlers defined here
        self.dp.add_handler(CommandHandler("start", handlers.start))
        self.dp.add_handler(CommandHandler("help", handlers.help))
        self.dp.add_handler(CommandHandler("test", handlers.test_handler))
        self.dp.add_handler(CommandHandler(
            "manager_stats",
            handlers.manager_stats_handler
        ))

        # on user message
        self.dp.add_handler(MessageHandler(
            Filters.text,
            handlers.handle_user_message)
        )

        # log all errors
        self.dp.add_error_handler(handlers.error)

    def run(self):
        # Start the Bot
        logger.info("Starting polling...")
        self.updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. start_polling() is non-blocking and will
        # stop the bot gracefully.
        self.updater.idle()
