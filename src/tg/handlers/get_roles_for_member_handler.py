import logging

from .utils import admin_only, reply
from src.app_context import AppContext
from src.roles.role_manager import RoleManager

logger = logging.getLogger(__name__)


@admin_only
def get_roles_for_member(update, tg_context):
    app_context = AppContext()
    # a hacky way of stripping the cmd from text
    member_name = ' '.join(update.message.text.strip().split(' ')[1:])
    roles = RoleManager(app_context.db_client).get_roles_for_member(member_name)
    reply(', '.join(roles), update)
