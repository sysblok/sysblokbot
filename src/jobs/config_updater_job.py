import datetime
import logging
from typing import Callable, List

from deepdiff import DeepDiff

from ..app_context import AppContext
from ..scheduler import JobScheduler
from ..trello.trello_client import TrelloClient


logger = logging.getLogger(__name__)


def execute(app_context: AppContext, send: Callable[[str], None]):
    """A very special job checking config for recent changes"""
    logger.info('Starting config_updater_job...')
    # get the scheduler instance
    job_scheduler = JobScheduler()
    # if anything at all changed in config
    diff = DeepDiff(
        job_scheduler.config,
        job_scheduler.config_manager.load_config_with_override()
    )
    if diff:
        logger.info(f'Config was changed, diff: {diff}')
        # update config['jobs']
        job_scheduler.reschedule_jobs()
        # update config['telegram']
        job_scheduler.telegram_sender.update_config(
            job_scheduler.config_manager.get_telegram_config()
        )
        # update config['trello']
        app_context.trello_client.update_config(
            job_scheduler.config_manager.get_trello_config())
        # TODO: update GS client too
    else:
        logger.info('No config changes detected')
    logger.info('Finished config_updater_job')
