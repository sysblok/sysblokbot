import datetime
import json
import logging
from typing import Callable

from deepdiff import DeepDiff
import html

from ..app_context import AppContext
from ..scheduler import JobScheduler
from ..strings import load
from ..tg.sender import TelegramSender
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class ConfigUpdaterJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        """A very special job checking config for recent changes"""
        # get the scheduler instance
        job_scheduler = JobScheduler()
        # if anything at all changed in config
        diff = DeepDiff(
            job_scheduler.config,
            job_scheduler.config_manager.load_jobs_config_with_override(),
            ignore_order=True,
            verbose_level=2
        )
        if diff:
            logger.info(f'Config was changed, diff: {diff}')
            try:
                diff = json.dumps(dict(diff), indent=2)
            except TypeError:
                pass
            TelegramSender().send_important_event(
                load('config_updater_job__config_diff', diff=html.escape(str(diff)))
            )
            try:
                # update config['jobs']
                job_scheduler.reschedule_jobs()
                # update config['telegram']
                tg_config = job_scheduler.config_manager.get_telegram_config()
                job_scheduler.telegram_sender.update_config(tg_config)
                app_context.tg_client.update_config(tg_config)
                # update admins and managers
                app_context.set_access_rights(tg_config)
                # update config['trello']
                app_context.trello_client.update_config(
                    job_scheduler.config_manager.get_trello_config())
                # update config['sheets']
                app_context.sheets_client.update_config(
                    job_scheduler.config_manager.get_sheets_config())
                # update config['drive']
                app_context.drive_client.update_config(
                    job_scheduler.config_manager.get_drive_config())
                # update config['db']
                app_context.db_client.update_config(
                    job_scheduler.config_manager.get_db_config())
                # update config['facebook']
                app_context.facebook_client.update_config(
                    job_scheduler.config_manager.get_facebook_config())
                # update config['instagram']
                app_context.instagram_client.update_config(
                    job_scheduler.config_manager.get_facebook_config())
                # update config['vk']
                app_context.vk_client.update_config(
                    job_scheduler.config_manager.get_vk_config())
                send(load('config_updater_job__config_changed'))
            except Exception as e:
                send(f'Failed to update config: {e}')
        else:
            logger.info('No config changes detected')
            send(load('config_updater_job__config_not_changed'))

    @staticmethod
    def _usage_muted():
        return True
