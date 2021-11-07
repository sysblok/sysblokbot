import logging
from sheetfu import Table
from sheetfu.modules.table import Item
from typing import Callable, List

from ..app_context import AppContext
from ..roles.roles import Roles
from ..sheets.sheets_objects import HRPersonRaw, HRPersonProcessed
from ..strings import load
from .base_job import BaseJob

from .utils import pretty_send

logger = logging.getLogger(__name__)


class HRCheckChatConsistencyJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        # get users that are in the main chat
        chat_id = app_context.tg_client.sysblok_chats['main_chat']
        chat_users = app_context.tg_client.get_chat_users(chat_id)
        # get users that _should_ be in the main chat <==> roles include Active or Frozen
        active_members = app_context.role_manager.get_members_for_role(Roles.ACTIVE_MEMBER.value)
        frozen_members = app_context.role_manager.get_members_for_role(Roles.FROZEN_MEMBER.value)
        chat_users_allowed = active_members + frozen_members

        unwanted_team_members = [
            f'{user.first_name} {user.last_name}' for user in chat_users
            if f'@{user.username}' not in [user.telegram for user in chat_users_allowed]
        ]
        missing_team_members = [
            user.name for user in chat_users_allowed
            if user.telegram not in [f'@{user.username}' for user in chat_users]
        ]
        paragraphs = [
            load(
                'hr_check_chat_consistency__message',
                missing_team_members=missing_team_members,
                unwanted_team_members=unwanted_team_members
            )
        ]
        pretty_send(paragraphs, send)
