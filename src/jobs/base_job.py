import logging
from typing import Callable

from ..app_context import AppContext
from .utils import job_log_start_stop


logger = logging.getLogger(__name__)


class BaseJob:
    @classmethod
    @job_log_start_stop
    def execute(
            cls,
            app_context: AppContext,
            send: Callable[[str], None] = lambda msg: None
    ):
        """
        Not intended to be overridden.
        Default send function does nothing with all send(...) statements.
        """
        try:
            cls._execute(app_context, send)
        except Exception as e:
            # should not raise exception, so that schedule module won't go mad retrying
            logger.error(f'Could not run job: {e}')

    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        """
        Must be overridden.
        """
        raise NotImplementedError('Job does not have _execute method implemented')

    @classmethod
    def __str__(cls):
        return cls.__module__
