import logging
from typing import Callable

from ..app_context import AppContext
from ..strings import load
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class DBFetchAllTeamMembersJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        team_size = app_context.db_client.fetch_authors_sheet(
            app_context.sheets_client
        )
        team_size += app_context.db_client.fetch_curators_sheet(
            app_context.sheets_client
        )
        team_size += app_context.db_client.fetch_team_sheet(
            app_context.sheets_client
        )
        # Do we need TODO this? Copied from db_fetch_team_sheet_job.py:
        # after we fetch the team, we need to recalculate the roles
        # app_context.role_manager.calculate_db_roles()
        logger.info(f"Fetched {team_size} team members")
        send(load("db_fetch_all_team_members_job__success", team_size=team_size))
