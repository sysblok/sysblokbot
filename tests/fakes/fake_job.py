import logging
import sys
sys.path.append("...")  # noqa hack to import BaseJob

from src.jobs.base_job import BaseJob

logger = logging.getLogger(__name__)


run_counter = 0


class FakeJob(BaseJob):
    @staticmethod
    def _execute(app_context, send):
        logger.info('FakeJob executing')
        global run_counter
        run_counter += 1


def reset_run_counter():
    global run_counter
    run_counter = 0
