import logging
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from .tg import handlers
from .tg.sender import TelegramSender
from .sheets.sheets_client import GoogleSheetsClient
from .trello.trello_client import TrelloClient


logger = logging.getLogger(__name__)


class SysBlokBot:
    def __init__(self, config):
        self.updater = Updater(config['telegram']['token'], use_context=True)
        self.dp = self.updater.dispatcher
        # TODO: Consider making them singletones
        self.telegram_sender = TelegramSender(
            self.dp.bot,
            config['chats'],
            config['telegram'].get('is_silent', True)
        )
        self.trello_client = TrelloClient(config=config['trello'])
        self.sheets_client = GoogleSheetsClient(
            api_key_path=config['sheets']['api_key_path'],
            curators_sheet_key=config['sheets']['curators_sheet_key'],
            authors_sheet_key=config['sheets']['authors_sheet_key']
        )

    def init_handlers(self):
        # all command handlers defined here
        self.dp.add_handler(CommandHandler("start", handlers.start))
        self.dp.add_handler(CommandHandler("help", handlers.help))
        self.dp.add_handler(CommandHandler("test", handlers.test_handler))

        # on user message
        self.dp.add_handler(MessageHandler(Filters.text, handlers.handle_user_message))

        # log all errors
        self.dp.add_error_handler(handlers.error)

    def run(self):
        # Start the Bot
        logger.info("Starting polling...")
        self.updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. start_polling() is non-blocking and will stop the bot gracefully.
        self.updater.idle()
