import logging

from src.app_context import AppContext
from src.roles.role_manager import RoleManager
from src.roles.roles import Roles
from src.strings import load

from .utils import admin_only, reply

logger = logging.getLogger(__name__)


@admin_only
def get_members_for_role(update, tg_context):
    app_context = AppContext()
    # a hacky way of stripping the cmd from text
    role_name = " ".join(update.message.text.strip().split(" ")[1:])
    members = RoleManager(app_context.db_client).get_members_for_role(role_name)
    if not members:
        available_roles = ", ".join(Roles.__members__.values())
        message = load("role_manager__role_not_found", available_roles=available_roles)
    else:
        message = load(
            "role_manager__role_members",
            role=role_name,
            members="\n".join([member.name for member in members]),
        )
    reply(message, update)
