import logging
from typing import Callable

from ..app_context import AppContext
from ..consts import USAGE_LOG_LEVEL

logger = logging.getLogger(__name__)


class BaseJob:
    @classmethod
    def execute(
            cls,
            app_context: AppContext,
            send: Callable[[str], None] = lambda msg: None,
            called_from_handler=False
    ):
        """
        Not intended to be overridden.
        Default send function does nothing with all send(...) statements.
        """
        module = cls.__name__
        if cls._usage_muted():
            logging_func = logger.info
        else:
            logging_func = logger.usage

        try:
            logging_func(f'Job {module} started...')
            cls._execute(app_context, send, called_from_handler)
            logging_func(f'Job {module} finished')
        except Exception as e:
            # should not raise exception, so that schedule module won't go mad retrying
            logging.exception(f'Could not run job {module}', exc_info=e)

    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        """
        Must be overridden.
        """
        raise NotImplementedError('Job does not have _execute method implemented')

    @classmethod
    def __str__(cls):
        return cls.__module__

    @classmethod
    def _usage_muted(cls):
        return False
