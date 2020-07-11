from typing import Callable

from ..app_context import AppContext
from ..strings import load
from .base_job import BaseJob


class SampleJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        # Logic here could include retrieving data from trello/sheets
        # and sending a notification to corresponding user.
        # app_context contain all necessary clients inside.
        send(load('sample_job__string', status='done'))
