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
        logger.warning(f'Admin-only handler {func.__name__} \
            was invoked by {update.message.chat_id}')
    return wrapper


# Command handlers
def start(update, tg_context):
    # TODO: register a new user somewhere, e.g. Google Sheet
    update.message.reply_text('''
Привет!

Я — бот Системного Блока. Меня создали для того, чтобы я помогал авторам, редакторам, кураторам и другим участникам проекта.

Например, я умею проводить субботники в Trello-доске и сообщать о найденных неточностях: карточках без авторов, сроков и тегов рубрик, а также авторах без карточек и карточках с пропущенным дедлайном. Для их исправления мне понадобится ваша помощь, без кожаных мешков пока не справляюсь.

Хорошего дня! Не болейте!
'''.strip())  # noqa


def help(update, tg_context):
    # TODO: add some help text
    update.message.reply_text('Здесь будет какая-нибудь инструкция')


@admin_only
def test_handler(update, tg_context):
    """
    Handler for /test command, feel free to use it for one-off job testing
    """
    app_context = AppContext()
    jobs.sample_job(app_context, None)


@admin_only
def manager_stats_handler(update, tg_context):
    app_context = AppContext()
    # TODO: switch to create_chat_ids_send
    jobs.manager_stats_job(app_context, send=TelegramSender().send_to_managers)


# TODO: @manager_only
def get_manager_stats_handler(update, tg_context):
    app_context = AppContext()
    jobs.manager_stats_job(
        app_context,
        send=TelegramSender().create_reply_send(update)
    )


# Other handlers
def handle_user_message(update, tg_context):
    # TODO: depending on user state, do anything (postpone the task, etc)
    if update.message is not None:
        logger.debug(
            f'Got {update.message.text} from {update.message.chat_id}'
        )


def error(update, tg_context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, tg_context.error)
