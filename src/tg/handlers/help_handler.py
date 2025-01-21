import logging

from ...consts import CommandCategories
from ...strings import load
from .utils import direct_message_only, is_sender_admin, is_sender_manager, reply

logger = logging.getLogger(__name__)


@direct_message_only
def help(update, tg_context, handlers_info: dict):
    message = ""

    for category_alias in sorted(handlers_info.keys(), key=lambda cat: cat.value):
        print(category_alias)
        if category_alias in [
            CommandCategories.DATA_SYNC,
            CommandCategories.CONFIG,
            CommandCategories.LOGGING,
            CommandCategories.DEBUG,
        ]:
            continue
        handlers = handlers_info[category_alias]
        listed_handlers = []
        if is_sender_admin(update):
            listed_handlers = list(handlers["admin"].items()) + list(
                handlers["manager"].items()
            )
        elif is_sender_manager(update):
            listed_handlers = list(handlers["manager"].items())
        listed_handlers += list(handlers["user"].items())

        if listed_handlers:
            message += _format_commands_block(category_alias, listed_handlers)

    if not message.strip():
        message = load("help__no_commands")
    else:
        message = f'{load("help__commands_list")}\n\n{message}'
    reply(message, update)


def _format_commands_block(category_alias: CommandCategories, handlers: list):
    lines = []
    for command, description in handlers:
        lines.append(f"{command} - {description}" if description else command)
    lines.sort()
    category = load(category_alias.value)
    if category:
        lines = [category, ""] + lines
    return "\n".join(lines) + "\n\n"
