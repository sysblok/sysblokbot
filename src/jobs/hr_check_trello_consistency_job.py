import logging

from typing import Callable, List

from ..app_context import AppContext
from ..roles.roles import Roles
from ..strings import load
from ..tg.sender import pretty_send
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class HRCheckTrelloConsistencyJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        # get users that are in the trello board
        trello_users = app_context.trello_client.get_members()
        # get users that _should_ be in the trello board <==> roles include Active or Frozen
        active_members = app_context.role_manager.get_members_for_role(Roles.ACTIVE_MEMBER)
        frozen_members = app_context.role_manager.get_members_for_role(Roles.FROZEN_MEMBER)
        trello_users_allowed = active_members + frozen_members

        unwanted_team_members = [
            f'{user.full_name} @{user.username}' for user in trello_users
            if not user.username or f'@{user.username.strip().lower()}' not in [
                user.trello.strip().lower() for user in trello_users_allowed if user.trello
            ]
        ]
        missing_team_members = [
            f'{user.name} {user.trello}' for user in active_members
            if not user.trello or user.trello.strip().lower() not in [
                f'@{user.username.strip().lower()}' for user in trello_users if user.username
            ]
        ]
        paragraphs = [
            load('hr_check_trello_consistency__message'),
            load(
                'hr_check_trello_consistency__missing',
                missing_team_members='\n'.join(missing_team_members),
            ),
            load(
                'hr_check_trello_consistency__unwanted',
                unwanted_team_members='\n'.join(unwanted_team_members)
            )
        ]
        pretty_send(paragraphs, send)
