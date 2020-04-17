"""
Module with all the telegram handlers.
"""
import logging

from ..jobs import jobs
from .sender import TelegramSender
from ..app_context import AppContext

logger = logging.getLogger(__name__)


def admin_only(func):
    def wrapper(update, tg_context, *args, **kwargs):
        app_context = AppContext()
        if update.message.chat_id in app_context.admin_chat_ids:
            return func(update, tg_context, *args, **kwargs)
        logger.warning(f'Admin-only handler {func.__name__} was invoked by {update.message.chat_id}')
    return wrapper


# Command handlers
def start(update, tg_context):
    # TODO: register a new user somewhere, e.g. Google Sheet
    update.message.reply_text('Ура! Теперь ты можешь получать обновления от этого бота!')


def help(update, tg_context):
    # TODO: add some help text
    update.message.reply_text('Здесь будет какая-нибудь инструкция')


@admin_only
def admin_handler(update, tg_context):
    update.message.reply_text('You are admin')


def test_handler(update, tg_context):
    """Handler for /test command, feel free to use it for one-off job testing"""
    app_context = AppContext()
    jobs.manager_stats_job(
        app_context,
        TelegramSender(
            tg_context.bot,
            app_context.config['chats'],
            app_context.config['telegram'].get('is_silent', True)
        )
    )


# Other handlers
def handle_user_message(update, tg_context):
    # TODO: depending on user state, do anything (postpone the task, etc)
    logger.info(f'Got {update.message.text} from {update.message.chat_id}')


def error(update, tg_context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, tg_context.error)
