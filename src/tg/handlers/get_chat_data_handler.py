import logging

from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
def get_chat_data(update, tg_context):
    reply(str(tg_context.chat_data), update)
