import logging

from .utils import direct_message_only, is_sender_admin, is_sender_manager, reply

logger = logging.getLogger(__name__)


@direct_message_only
def help(update, tg_context, admin_handlers, manager_handlers, user_handlers):
    message = ''
    # list privileged commands
    if is_sender_admin(update):
        message += _format_commands_block(admin_handlers)
        message += _format_commands_block(manager_handlers)
    elif is_sender_manager(update):
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
