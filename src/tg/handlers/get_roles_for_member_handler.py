import json
import logging

from src.app_context import AppContext
from src.roles.role_manager import RoleManager
from src.strings import load

from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
async def get_roles_for_member(update, tg_context):
    app_context = AppContext()
    # a hacky way of stripping the cmd from text
    member_name = " ".join(update.message.text.strip().split(" ")[1:])
    member = RoleManager(app_context.db_client).get_member(member_name)
    if not member:
        message = load("role_manager__member_not_found")
    else:
        roles = json.loads(member.roles)
        message = load(
            "role_manager__member_roles", username=member.name, roles=", ".join(roles)
        )
    await reply(message, update)
