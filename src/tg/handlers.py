"""
Module with all the telegram handlers.
"""
import logging

from ..jobs import jobs
from .. import bot

logger = logging.getLogger(__name__)


# Command handlers
def start(update, context):
    # TODO: register a new user somewhere, e.g. Google Sheet
    update.message.reply_text('Ура! Теперь ты можешь получать обновления от этого бота!')


def help(update, context):
    # TODO: add some help text
    update.message.reply_text('Здесь будет какая-нибудь инструкция')


def test_handler(update, context):
    """Handler for /test command, feel free to use it for one-off job testing"""
    jobs.manager_stats_job(
        bot.trello_client,
        bot.telegram_sender,
        bot.config['trello']['_tmp_']['list_aliases']  # TODO: remove this
    )


# Other handlers
def handle_user_message(update, context):
    # TODO: depending on user state, do anything (postpone the task, etc)
    logger.info(f'Got {update.message.text} from {update.message.chat_id}')


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)
