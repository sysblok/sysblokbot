import logging
from sheetfu import Table
from sheetfu.modules.table import Item
from typing import Callable

from ..app_context import AppContext
from ..roles.roles import Roles
from ..strings import load
from ..tg.sender import pretty_send
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class HRCheckChatConsistencyFrozenJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        # get users that are in the main chat
        chat_users = app_context.tg_client.get_main_chat_users()
        # get Frozen users
        frozen_members = app_context.role_manager.get_members_for_role(
            Roles.FROZEN_MEMBER
        )

        frozen_in_chat = [
            f"{user.name} {user.telegram}"
            for user in frozen_members
            if user.telegram
            and user.telegram.strip().lower()
            in [
                f"@{user.username.strip().lower()}"
                for user in chat_users
                if user.username
            ]
        ]
        frozen_not_in_chat = [
            f"{user.name} {user.telegram}"
            for user in frozen_members
            if not user.telegram
            or user.telegram.strip().lower()
            not in [
                f"@{user.username.strip().lower()}"
                for user in chat_users
                if user.username
            ]
        ]
        paragraphs = [
            load("hr_check_chat_consistency_frozen__message"),
            load(
                "hr_check_chat_consistency_frozen__in_chat",
                frozen_in_chat="\n".join(frozen_in_chat),
            ),
            load(
                "hr_check_chat_consistency_frozen__not_in_chat",
                frozen_not_in_chat="\n".join(frozen_not_in_chat),
            ),
        ]
        pretty_send(paragraphs, send)
