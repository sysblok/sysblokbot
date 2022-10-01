import logging
import json

from .utils import admin_only, reply
from src.app_context import AppContext
from src.strings import load
from src.roles.role_manager import RoleManager

logger = logging.getLogger(__name__)


@admin_only
def get_roles_for_member(update, tg_context):
    app_context = AppContext()
    # a hacky way of stripping the cmd from text
    member_name = ' '.join(update.message.text.strip().split(' ')[1:])
    member = RoleManager(app_context.db_client).get_member(member_name)
    if not member:
        message = load('role_manager__member_not_found')
    else:
        roles = json.loads(member.roles)
        message = load('role_manager__member_roles', username=member.name, roles=', '.join(roles))
    reply(message, update)
