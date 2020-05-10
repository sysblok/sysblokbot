"""
Module with all the telegram handlers.
"""
import json
import logging

from . import utils as tg_utils
from .utils import admin_only, manager_only, direct_message_only, reply
from .. import jobs
from ..app_context import AppContext
from ..config_manager import ConfigManager
from ..scheduler import JobScheduler
from ..tg.sender import TelegramSender
from ..utils.log_handler import ErrorBroadcastHandler

logger = logging.getLogger(__name__)


# Command handlers
def start(update, tg_context):
    sender_id = tg_utils.get_sender_id(update)
    if tg_utils.is_group_chat(update) and not tg_utils.is_sender_admin(update):
        logger.warning(
            f'/start was invoked in a group {update.message.chat_id} by {sender_id}'
        )
        return
    reply('''
Привет!

Я — бот Системного Блока. Меня создали для того, чтобы я помогал авторам, редакторам, кураторам и другим участникам проекта.

Например, я умею проводить субботники в Trello-доске и сообщать о найденных неточностях: карточках без авторов, сроков и тегов рубрик, а также авторах без карточек и карточках с пропущенным дедлайном. Для их исправления мне понадобится ваша помощь, без кожаных мешков пока не справляюсь.

Хорошего дня! Не болейте!
'''.strip(), update)  # noqa


@direct_message_only
def help(update, tg_context, admin_handlers, manager_handlers, user_handlers):
    message = ''
    # list privileged commands
    if tg_utils.is_sender_admin(update):
        message += _format_commands_block(admin_handlers)
        message += _format_commands_block(manager_handlers)
    elif tg_utils.is_sender_manager(update):
        message += _format_commands_block(manager_handlers)

    # list common commands
    message += _format_commands_block(user_handlers)

    if not message.strip():
        message = 'Кажется, у меня пока нет доступных команд для тебя.'
    else:
        message = '<b>Список команд</b>:\n\n' + message
    reply(message, update)


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
    reply('\n'.join(JobScheduler.list_jobs()), update)


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
    reply(f'Log level set to {logging.getLogger().level}', update)


@admin_only
def mute_errors(update, tg_context):
    ErrorBroadcastHandler().set_muted(True)
    reply(
        'I\'ll stop sending errors to important_events_recipients (until unmuted or restarted)!',
        update
    )


@admin_only
def unmute_errors(update, tg_context):
    ErrorBroadcastHandler().set_muted(False)
    reply(
        'I\'ll be sending error logs to important_events_recipients list!',
        update
    )


@admin_only
def get_config(update, tg_context):
    config = ConfigManager().get_latest_config()
    try:
        tokens = update.message.text.strip().split()
        config_path = tokens[1] if len(tokens) > 1 else ''
        if config_path:
            for config_item in config_path.split('.'):
                config = config[config_item]
    except Exception as e:
        reply('<b>Usage example:</b>\n/get_config jobs.sample_job', update)
        logger.warning(f'Failed to get config: {e}')
        return
    reply(f'<code>{json.dumps(ConfigManager.redact(config), indent=2)}</code>', update)


@admin_only
def set_config(update, tg_context):
    config_manager = ConfigManager()
    current_config = config_manager.get_latest_config()
    try:
        tokens = update.message.text.strip().split(maxsplit=2)
        assert len(tokens) == 3
        config_path = tokens[1]
        new_value = json.loads(tokens[2])
        for config_item in config_path.split('.'):
            current_config = current_config[config_item]

        if isinstance(current_config, dict):
            reply((
                f'Subconfig <code>{config_path}</code> is a complex object. '
                'Dict reassignment is not supported. '
                'Please, specify your request to str, bool, int or list'
            ), update)
            return
        if type(current_config) != type(new_value):
            reply((
                f'Type mismatch. Old value was <code>{type(current_config).__name__}</code>, '
                f'new value is <code>{type(new_value).__name__}</code>. '
                'Try /get_config to see current value format'
            ), update)
            return
        if current_config == new_value:
            reply('New value equals to existing. Nothing was updated', update)
            return

        config_manager.set_value_to_config_override(config_path, new_value)
        reply((
            f'Successfully updated!\n'
            f'Old value: <code>{current_config}</code>\n'
            f'New value: <code>{new_value}</code>'
        ), update)
    except Exception as e:
        reply((
            '<b>Usage example:</b>\n/set_config jobs.sample_job.at "15:00"\n\n'
            'Try to /get_config first and follow the existing format'
        ), update)
        logger.warning(f'Failed to set config: {e}')
        return

    # run config update job after config_override successfully updated
    chat_ids = config_manager.get_job_send_to('config_updater_job')
    jobs.ConfigUpdaterJob.execute(AppContext(), TelegramSender().create_chat_ids_send(chat_ids))


# Other handlers
def handle_user_message(update, tg_context):
    # TODO: depending on user state, do anything (postpone the task, etc)
    if update.message is not None:
        logger.debug(
            f'Got {update.message.text} from {update.message.chat_id}'
        )


def error(update, tg_context):
    """Log Errors caused by Updates."""
    logger.error('Update "%s" caused error "%s"', update, tg_context.error)
