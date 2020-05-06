import logging

from ..app_context import AppContext

logger = logging.getLogger(__name__)


def admin_only(func):
    """
    Decorator allowing only users from admin_chat_ids to run the command.
    Checks the immediate sender: if forwarded by non-admin, it doesn't run handler.
    If admin sends command to the chat, it does run handler.
    """
    def wrapper(update, tg_context, *args, **kwargs):
        if is_sender_admin(update):
            return func(update, tg_context, *args, **kwargs)
        logger.warning(f'Admin-only handler {func.__name__} \
            was invoked by {get_sender_id(update)}')
    return wrapper


def manager_only(func):
    """
    Decorator allowing only users from manager_chat_ids OR admin_chat_ids to run the command.
    Checks the immediate sender: if forwarded by non-manager, it doesn't run handler.
    If manager sends command to the chat, it does run handler.
    """
    def wrapper(update, tg_context, *args, **kwargs):
        if is_sender_manager(update) or is_sender_admin(update):
            return func(update, tg_context, *args, **kwargs)
        logger.warning(f'Manager-only handler {func.__name__} \
            was invoked by {get_sender_id(update)}')
    return wrapper


def direct_message_only(func):
    """
    Decorator disallowing users to call command in chats.
    Can be used along with other restriction decorators.
    """
    def wrapper(update, tg_context, *args, **kwargs):
        if not is_group_chat(update):
            return func(update, tg_context, *args, **kwargs)
        logger.warning(f'DM-only handler {func.__name__} \
            was invoked by {get_sender_id(update)}')
    return wrapper


def is_sender_admin(update) -> bool:
    chats = AppContext().admin_chat_ids
    return get_sender_id(update) in chats or get_sender_username(update) in chats


def is_sender_manager(update) -> bool:
    chats = AppContext().manager_chat_ids
    return get_sender_id(update) in chats or get_sender_username(update) in chats


def get_sender_id(update) -> int:
    return update.message.from_user.id


def get_chat_id(update) -> int:
    return update.message.chat_id


def get_sender_username(update) -> str:
    return update.message.from_user.username


def is_group_chat(update) -> bool:
    return update.message.chat.type in ('group', 'supergroup')
