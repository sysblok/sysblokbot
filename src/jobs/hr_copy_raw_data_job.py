from typing import Callable

from ..app_context import AppContext
from ..strings import load
from .base_job import BaseJob


class HRCopyRawDataJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        team_raw = app_context.sheets_client.fetch_team_raw()