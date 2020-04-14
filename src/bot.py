import logging
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from .scheduler import JobScheduler
from .config_manager import ConfigManager
from .tg import handlers
from .tg.sender import TelegramSender
from .sheets.sheets_client import GoogleSheetsClient
from .trello.trello_client import TrelloClient

ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, 'config.json')
CONFIG_OVERRIDE_PATH = os.path.join(ROOT_DIR, 'config_override.json')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


# Global client instances
# TODO: Consider making them singletones instead
trello_client = None
sheets_client = None
telegram_sender = None


def run():
    config = ConfigManager(
        CONFIG_PATH, CONFIG_OVERRIDE_PATH
    ).load_config_with_override()
    if not config:
        raise ValueError(f"Could not load config, can't go on")

    updater = Updater(config['telegram']['token'], use_context=True)
    dp = updater.dispatcher

    global trello_client, sheets_client, telegram_sender
    telegram_sender = TelegramSender(
        dp.bot,
        config['chats'],
        config['telegram'].get('is_silent', True)
    )
    trello_client = TrelloClient(config=config['trello'])
    sheets_client = GoogleSheetsClient(api_key_path=config['sheets']['api_key_path'])

    scheduler = JobScheduler(config, trello_client, sheets_client, telegram_sender)
    scheduler.init_jobs()

    # all command handlers defined here
    dp.add_handler(CommandHandler("start", handlers.start))
    dp.add_handler(CommandHandler("help", handlers.help))
    dp.add_handler(CommandHandler("test", handlers.test_handler))

    # on user message
    dp.add_handler(MessageHandler(Filters.text, handlers.handle_user_message))

    # log all errors
    dp.add_error_handler(handlers.error)

    # Start the Bot
    logger.info("Starting polling...")
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
