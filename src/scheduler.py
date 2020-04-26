import logging
import time
import threading

from deepdiff import DeepDiff
import schedule
import telegram

from .app_context import AppContext
from .config_manager import ConfigManager
from .consts import CONFIG_RELOAD_MINUTES
from .jobs import jobs
from .tg.sender import TelegramSender
from .utils.singleton import Singleton


logger = logging.getLogger(__name__)

CUSTOM_JOB_TAG = 'custom'
TECHNICAL_JOB_TAG = 'technical'


class JobScheduler(Singleton):
    """
    Don't forget to call run() after initializing.
    """
    def __init__(self, config: dict = None):
        if self.was_initialized():
            return

        logger.info("Creating JobScheduler instance")
        # save current config to track changes
        self.config = config
        # use config manager to receive current config states
        self.config_manager = ConfigManager()
        # re-read config on schedule
        schedule.every(CONFIG_RELOAD_MINUTES).minutes.do(
            self.config_checker_job
        ).tag(TECHNICAL_JOB_TAG)

    def run(self):
        logger.info('Starting JobScheduler...')
        self.app_context = AppContext()
        self.telegram_sender = TelegramSender()

        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease_continuous_run.is_set():
                    try:
                        schedule.run_pending()
                    except Exception as e:
                        logger.error(
                            f'Error while running scheduled jobs: {e}')
                    time.sleep(1)
                return cease_continuous_run

        continuous_thread = ScheduleThread()
        continuous_thread.start()
        self.stop_run_event = cease_continuous_run

    def config_checker_job(self):
        """A very special job checking config for recent changes"""
        # if anything at all changed in config
        diff = DeepDiff(
            self.config,
            self.config_manager.load_config_with_override()
        )
        if diff:
            logger.info(f'Config was changed, diff: {diff}')
            # update config['jobs']
            self.reschedule_jobs()
            # update config['telegram']
            self.telegram_sender.update_config(
                self.config_manager.get_telegram_config()
            )
            # update config['trello']
            self.app_context.trello_client.update_config(
                self.config_manager.get_trello_config())
            # TODO: update GS client too
        else:
            logger.info('No config changes detected')

    def init_jobs(self):
        """
        Initializing jobs on latest config state.
        """
        logger.info('Starting setting job schedules...')
        jobs_config = self.config_manager.get_jobs_config()
        for job_id, schedule_dict in jobs_config.items():
            try:
                job = getattr(jobs, job_id)
            except Exception as e:
                logger.error(f'Job "{job_id}" not found: {e}')
                continue
            logger.info(f'Found job "{job_id}"')
            try:
                scheduled = getattr(schedule.every(), schedule_dict['every'])
                if 'at' in schedule_dict:
                    scheduled = scheduled.at(schedule_dict['at'])
                # TODO: switch to send=sender.create_chat_ids_send(chat_ids)
                scheduled.do(
                    job,
                    app_context=self.app_context,
                    send=self.telegram_sender.send_to_managers
                ).tag(CUSTOM_JOB_TAG)
            except Exception as e:
                logger.error(f'Failed to schedule job {job_id} \
                    with params {schedule_dict}: {e}')
        logger.info('Finished setting jobs')

    def reschedule_jobs(self):
        logger.info('Clearing all scheduled jobs...')
        # clear only jobs originating from config
        schedule.clear(CUSTOM_JOB_TAG)
        self.config = self.config_manager.get_latest_config()
        self.init_jobs()

    def stop_running(self):
        '''Set a stopping event so we can finish last job gracefully'''
        logger.info((
            'Scheduler received a signal. '
            'Will terminate after ongoing jobs end'))
        self.stop_run_event.set()
