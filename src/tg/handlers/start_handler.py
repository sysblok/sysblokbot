import logging

from .utils import is_sender_admin, is_group_chat, get_sender_id, reply
from ...strings import load

logger = logging.getLogger(__name__)


def start(update, tg_context):
    sender_id = get_sender_id(update)
    if is_group_chat(update) and not is_sender_admin(update):
        logger.warning(
            f"/start was invoked in a group {update.message.chat_id} by {sender_id}"
        )
        return
    reply(load("start_handler__message"), update)  # noqa
