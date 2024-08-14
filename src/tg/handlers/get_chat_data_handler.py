import logging

from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
async def get_chat_data(update, tg_context):
    await reply(str(tg_context.chat_data), update)
