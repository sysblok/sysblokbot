"""
Module with all the telegram handlers.
"""
import logging

from . import utils as tg_utils
from .sender import TelegramSender
from .utils import admin_only, manager_only, direct_message_only
from .. import jobs
from ..app_context import AppContext
from ..scheduler import JobScheduler

logger = logging.getLogger(__name__)


# Command handlers
def start(update, tg_context):
    sender_id = tg_utils.get_sender_id(update)
    if tg_utils.is_group_chat(update) and not tg_utils.is_sender_admin(update):
        logger.warning(
            f'/start was invoked in a group {update.message.chat_id} by {sender_id}'
        )
        return
    update.message.reply_text('''
Привет!

Я — бот Системного Блока. Меня создали для того, чтобы я помогал авторам, редакторам, кураторам и другим участникам проекта.

Например, я умею проводить субботники в Trello-доске и сообщать о найденных неточностях: карточках без авторов, сроков и тегов рубрик, а также авторах без карточек и карточках с пропущенным дедлайном. Для их исправления мне понадобится ваша помощь, без кожаных мешков пока не справляюсь.

Хорошего дня! Не болейте!
'''.strip())  # noqa


@direct_message_only
def help(update, tg_context, admin_handlers, manager_handlers, user_handlers):
    message = ''
    if tg_utils.is_sender_admin(update):
        message += _format_commands_block(admin_handlers)
    if tg_utils.is_sender_manager(update):
        message += _format_commands_block(manager_handlers)
    message += _format_commands_block(user_handlers)
    if not message.strip():
        message = 'Кажется, у меня пока нет доступных команд для тебя.'
    else:
        message = '<b>Список команд</b>:\n\n' + message
    TelegramSender().send_to_chat_id(message, tg_utils.get_chat_id(update))


def _format_commands_block(handlers: dict):
    lines = []
    for command, description in handlers.items():
        lines.append(f'{command} - {description}' if description else command)
    return '\n'.join(lines) + '\n\n'


@admin_only
def test_handler(update, tg_context):
    """
    Handler for /test command, feel free to use it for one-off job testing
    """
    jobs.sample_job.SampleJob.execute(AppContext(), None)


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
