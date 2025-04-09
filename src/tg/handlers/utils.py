import logging

from ...app_context import AppContext
from ...tg.sender import pretty_send
from ..sender import TelegramSender

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
        logger.warning(
            f"Admin-only handler {func.__name__} invoked by {get_sender_id(update)}"
        )

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
        logger.usage(
            f"Manager-only handler {func.__name__} invoked by {get_sender_id(update)}"
        )

    return wrapper


def direct_message_only(func):
    """
    Decorator disallowing users to call command in chats.
    Can be used along with other restriction decorators.
    """

    def wrapper(update, tg_context, *args, **kwargs):
        if not is_group_chat(update):
            return func(update, tg_context, *args, **kwargs)
        logger.warning(
            f"DM-only handler {func.__name__} invoked by {get_sender_id(update)}"
        )

    return wrapper


def is_sender_admin(update) -> bool:
    chats = AppContext().admin_chat_ids
    return get_sender_id(update) in chats or get_sender_username(update) in chats


def is_sender_manager(update) -> bool:
    telegram_login = get_chat_name(update)
    curator = AppContext().db_client.get_curator_by_telegram(telegram_login)
    return curator is not None


def get_sender_id(update) -> int:
    if update.message:
        return update.message.from_user.id
    elif update.callback_query:
        return update.callback_query.from_user.id


def get_chat_id(update) -> int:
    if update.message is not None:
        return update.message.chat_id
    return update.callback_query.message.chat_id


def get_chat_name(update) -> str:
    if update.message is not None:
        return update.message.chat.title or update.message.chat.username
    return ""


def get_sender_username(update) -> str:
    return update.message.from_user.username


def is_group_chat(update) -> bool:
    return update.message.chat.type in ("group", "supergroup")


def reply(message: str, tg_update, **kwargs):
    return pretty_send(
        [message],
        lambda msg: TelegramSender().send_to_chat_id(
            msg, get_chat_id(tg_update), **kwargs
        ),
    )
