import logging
import os
from typing import Callable

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from .app_context import AppContext
from .config_manager import ConfigManager
from .consts import SEND_TO
from .jobs import jobs
from .tg import handlers, sender


logger = logging.getLogger(__name__)


class SysBlokBot:
    def __init__(self, config_manager: ConfigManager, signal_handler):
        self.config_manager = config_manager
        tg_config = config_manager.get_telegram_config()
        self.updater = Updater(
            tg_config['token'],
            use_context=True,
            user_sig_handler=signal_handler,
        )
        self.dp = self.updater.dispatcher
        self.app_context = AppContext(config_manager)
        self.telegram_sender = sender.TelegramSender(self.dp.bot, tg_config)

    def init_handlers(self):
        # all command handlers defined here
        self.dp.add_handler(CommandHandler("start", handlers.start))
        self.dp.add_handler(CommandHandler("help", handlers.help))
        self.dp.add_handler(CommandHandler("test", handlers.test_handler))
        self.dp.add_handler(CommandHandler(
            "send_trello_board_state",
            self.admin_handler("manager_stats_job")))
            
        self.dp.add_handler(CommandHandler(
            "get_trello_board_state",
            self.manager_handler("manager_stats_job")))

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
    
    def admin_handler(self, job_name: str) -> Callable:
        """
        Handler that invokes the job as configured in settings, if called by admin.
        Can possibly send message to multiple chat ids, if configured in settings.
        """
        return handlers.admin_only(self._create_broadcast_handler(job_name))

    def manager_handler(self, job_name: str) -> Callable:
        """
        Handler that replies if manager invokes it (DM or chat).
        """
        return handlers.manager_only(self._create_reply_handler(job_name))
    
    def user_handler(self, job_name: str) -> Callable:
        """
        Handler that replies to any user.
        """
        return self._create_reply_handler(job_name)

    def _create_reply_handler(self, job_name: str) -> Callable:
        """
        Creates a handler that replies to a message of given user.
        """
        return lambda update, tg_context: getattr(jobs, job_name)(
                app_context=self.app_context,
                send=self.telegram_sender.create_reply_send(update)
            )

    def _create_broadcast_handler(self, job_name: str) -> Callable:
        """
        Creates a handler that sends message to list of chat ids.
        """
        chat_ids =self.config_manager.get_jobs_config()[job_name].get(SEND_TO, [])
        return lambda update, tg_context: getattr(jobs, job_name)(
                app_context=self.app_context,
                send=self.telegram_sender.create_chat_ids_send(chat_ids)
            )
