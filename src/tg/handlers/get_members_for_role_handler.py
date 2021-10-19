import logging

from .utils import admin_only, reply
from src.app_context import AppContext
from src.roles.roles_manager import RolesManager

logger = logging.getLogger(__name__)


@admin_only
def get_members_for_role(update, tg_context):
    app_context = AppContext()
    # a hacky way of stripping the cmd from text
    role_name = ' '.join(update.message.text.strip().split(' ')[1:])
    reply(RolesManager(app_context.db_client).get_members_for_role(role_name), update)
