import json
import logging

from .utils import admin_only, reply
from ... import consts, jobs
from ...app_context import AppContext
from ...config_manager import ConfigManager
from ...tg.sender import TelegramSender


logger = logging.getLogger(__name__)


@admin_only
def db_fetch_trello_state(update, tg_context):
    app_context = AppContext()
    try:
        app_context.db_client.fetch_trello_list_ids(app_context.trello_client)
        app_context.db_client.fetch_trello_custom_field_types(app_context.trello_client)
    except Exception:
        reply('Can\'t update Trello data in db.', update)
        return
    reply('Successfully updated Trello data in db.', update)
