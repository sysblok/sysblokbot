import logging
from typing import Callable

from sheetfu import Table
from sheetfu.modules.table import Item

from ..app_context import AppContext
from ..roles.roles import Roles
from ..strings import load
from ..tg.sender import pretty_send
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class HRCheckTrelloConsistencyFrozenJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        # get users that are in the trello board
        trello_users = app_context.trello_client.get_members()
        # get Frozen users
        frozen_members = app_context.role_manager.get_members_for_role(
            Roles.FROZEN_MEMBER
        )

        frozen_in_trello = [
            f"{user.name} {user.trello}"
            for user in frozen_members
            if user.trello
            and user.trello.strip().lower()
            in [
                f"@{user.username.strip().lower()}"
                for user in trello_users
                if user.username
            ]
        ]
        frozen_not_in_trello = [
            f"{user.name} {user.trello}"
            for user in frozen_members
            if not user.trello
            or user.trello.strip().lower()
            not in [
                f"@{user.username.strip().lower()}"
                for user in trello_users
                if user.username
            ]
        ]
        paragraphs = [
            load("hr_check_trello_consistency_frozen__message"),
            load(
                "hr_check_trello_consistency_frozen__in_trello",
                frozen_in_trello="\n".join(frozen_in_trello),
            ),
            load(
                "hr_check_trello_consistency_frozen__not_in_trello",
                frozen_not_in_trello="\n".join(frozen_not_in_trello),
            ),
        ]
        pretty_send(paragraphs, send)
