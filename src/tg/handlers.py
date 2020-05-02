"""
Module with all the telegram handlers.
"""
import logging

from .. import jobs
from .sender import TelegramSender
from ..app_context import AppContext
from ..scheduler import JobScheduler

logger = logging.getLogger(__name__)


def admin_only(func):
    """
    Decorator allowing only users from admin_chat_ids to run the command.
    Checks the immediate sender: if forwarded by non-admin, it doesn't run handler.
    If admin sends command to the chat, it does run handler.
    """
    def wrapper(update, tg_context, *args, **kwargs):
        if _is_sender_admin(update):
            return func(update, tg_context, *args, **kwargs)
        logger.warning(f'Admin-only handler {func.__name__} \
            was invoked by {_get_sender_id(update)}')
    return wrapper


def manager_only(func):
    """
    Decorator allowing only users from manager_chat_ids OR admin_chat_ids to run the command.
    Checks the immediate sender: if forwarded by non-manager, it doesn't run handler.
    If manager sends command to the chat, it does run handler.
    """
    def wrapper(update, tg_context, *args, **kwargs):
        if _is_sender_manager(update) or _is_sender_admin(update):
            return func(update, tg_context, *args, **kwargs)
        logger.warning(f'Manager-only handler {func.__name__} \
            was invoked by {_get_sender_id(update)}')
    return wrapper


# Command handlers
def start(update, tg_context):
    is_group = update.message.chat.type in ('group', 'supergroup')
    if is_group and not _is_sender_admin(update):
        logger.warning(
            f'/start was invoked in a group {update.message.chat_id} by {_get_sender_id(update)}'
        )
        return
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
    jobs.sample_job(AppContext(), None)


@admin_only
def list_jobs_handler(update, tg_context):
    update.message.reply_text('\n'.join(JobScheduler.list_jobs()))


@admin_only
def set_log_level_handler(update, tg_context):
    level = update.message.text.strip().split()[-1].upper()
    try:
        if level == 'DEBUG':
            logging.getLogger().setLevel(logging.DEBUG)
        elif level == 'INFO':
            logging.getLogger().setLevel(logging.INFO)
    except Exception as e:
        logger.error(f'Failed to update log level to {level}: {e}')
    update.message.reply_text(f'Log level set to {logging.getLogger().level}')


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


def _is_sender_admin(update) -> bool:
    chats = AppContext().admin_chat_ids
    return _get_sender_id(update) in chats or _get_sender_username(update) in chats


def _is_sender_manager(update) -> bool:
    chats = AppContext().manager_chat_ids
    return _get_sender_id(update) in chats or _get_sender_username(update) in chats


def _get_sender_id(update) -> int:
    return update.message.from_user.id


def _get_sender_username(update) -> str:
    return update.message.from_user.username
