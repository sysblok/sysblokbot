from typing import Callable

from ..app_context import AppContext
from .base_job import BaseJob


class SampleJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        # Logic here could include retrieving data from trello/sheets
        # and sending a notification to corresponding user.
        # app_context contain all necessary clients inside.
        send(app_context.db_client.get_string('some_string'))
