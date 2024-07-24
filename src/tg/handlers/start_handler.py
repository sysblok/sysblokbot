import logging

from ...strings import load
from .utils import get_sender_id, is_group_chat, is_sender_admin, reply

logger = logging.getLogger(__name__)


async def start(update, tg_context):
    sender_id = get_sender_id(update)
    if is_group_chat(update) and not is_sender_admin(update):
        logger.warning(
            f"/start was invoked in a group {update.message.chat_id} by {sender_id}"
        )
        return
    await reply(load("start_handler__message"), update)  # noqa
