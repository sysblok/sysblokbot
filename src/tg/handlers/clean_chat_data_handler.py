import logging

from ...strings import load
from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
async def clean_chat_data(update, tg_context):
    tg_context.chat_data.clear()
    await reply("cleaned", update)
