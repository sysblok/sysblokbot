from typing import Callable

from ..app_context import AppContext
from .base_job import BaseJob


class ShrugJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False,
        *argc, **argv
    ):
        send("¯\\_(ツ)_/¯")
