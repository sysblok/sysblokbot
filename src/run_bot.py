import logging
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from .scheduler import JobScheduler
from .config_manager import ConfigManager

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(ROOT_DIR, '../config.json')
CONFIG_OVERRIDE_PATH = os.path.join(ROOT_DIR, '../config_override.json')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)


# Command handlers
def start(update, context):
    # TODO: register a new user somewhere, e.g. Google Sheet
    update.message.reply_text('Welcome text will be here!')


def help(update, context):
    # TODO: add some help text
    update.message.reply_text('Help text will be here')

# Other handlers
def handle_user_message(update, context):
    # TODO: depending on user state, do anything (postpone the task, etc)
    # Now echoes the message
    update.message.reply_text(update.message.text)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    config = ConfigManager(
        CONFIG_PATH, CONFIG_OVERRIDE_PATH
    ).load_config_with_override()
    if not config:
        raise ValueError(f"Could not load config, can't go on")

    updater = Updater(config['telegram']['token'], use_context=True)
    dp = updater.dispatcher

    scheduler = JobScheduler(config)
    scheduler.init_jobs()

    # all command handlers defined here
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    # on user message
    dp.add_handler(MessageHandler(Filters.text, handle_user_message))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
