#!/usr/bin/env python3

import json
import logging
import os

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

from scheduler import JobScheduler

CONFIG_PATH = os.path.join(
    os.path.abspath(os.path.dirname(__file__)),
    'config.json'
)
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

def load_config() -> dict:
    try:
        with open(CONFIG_PATH) as fin:
            try:
                return json.loads(fin.read())
            except json.JSONDecodeError as e:
                logger.error(e)
    except IOError:
        logger.error(f'Config file at {CONFIG_PATH} not found')

def main():
    config = load_config()
    if config is None:
        raise ValueError(f"Could not load {CONFIG_PATH}, can't go on")

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


if __name__ == '__main__':
    main()