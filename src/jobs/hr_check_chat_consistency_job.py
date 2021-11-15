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
        chat_users = app_context.tg_client.get_main_chat_users()
        # get users that _should_ be in the main chat <==> roles include Active or Frozen
        active_members = app_context.role_manager.get_members_for_role(Roles.ACTIVE_MEMBER)
        frozen_members = app_context.role_manager.get_members_for_role(Roles.FROZEN_MEMBER)
        chat_users_allowed = active_members + frozen_members

        unwanted_team_members = [
            f'{user.first_name} {user.last_name} @{user.username}' for user in chat_users
            if not user.username or f'@{user.username.strip().lower()}' not in [
                user.telegram.strip().lower() for user in chat_users_allowed if user.telegram
            ]
        ]
        missing_team_members = [
            f'{user.name} {user.telegram}' for user in active_members
            if not user.telegram or user.telegram.strip().lower() not in [
                f'@{user.username.strip().lower()}' for user in chat_users if user.username
            ]
        ]
        paragraphs = [
            load('hr_check_chat_consistency__message'),
            load(
                'hr_check_chat_consistency__missing',
                missing_team_members='\n'.join(missing_team_members),
            ),
            load(
                'hr_check_chat_consistency__unwanted',
                unwanted_team_members='\n'.join(unwanted_team_members)
            )
        ]
        pretty_send(paragraphs, send)
