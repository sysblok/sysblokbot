import logging

from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
def clean_chat_data(update, tg_context):
    tg_context.chat_data.clear()
    reply("cleaned", update)
