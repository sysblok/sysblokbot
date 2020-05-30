from typing import Callable

from ..app_context import AppContext
from .base_job import BaseJob


class SampleJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        # Logic here could include retrieving data from trello/sheets
        # and sending a notification to corresponding user.
        # app_context contain all necessary clients inside.
        send("I am a job and I'm done")
