import logging
import time
import threading

from deepdiff import DeepDiff
import schedule
import telegram

from .bot import SysBlokBot
from .config_manager import ConfigManager
from .consts import CONFIG_PATH, CONFIG_OVERRIDE_PATH
from .jobs import jobs
from .tg.sender import TelegramSender


logger = logging.getLogger(__name__)

CUSTOM_JOB_TAG = 'custom'
TECHNICAL_JOB_TAG = 'technical'


class JobScheduler:
    def __init__(self):
        logger.info('Created empty JobScheduler, call initialize(config, bot)')
        
    def initialize(self, config: dict, bot: SysBlokBot):
        logger.info('Initializing JobScheduler...')
        self.config = config
        self.app_context = bot.app_context
        self.sender = TelegramSender(
            bot,
            config['chats'],
            config['telegram'].get('is_silent', True)
        )
        # re-read config
        schedule.every(15).minutes.do(self.config_checker_job).tag(TECHNICAL_JOB_TAG)

        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease_continuous_run.is_set():
                    try:
                        schedule.run_pending()
                    except Exception as e:
                        logger.error(f'Error while running scheduled jobs: {e}')
                    time.sleep(1)
                return cease_continuous_run

        continuous_thread = ScheduleThread()
        continuous_thread.start()
        self.stop_run_event = cease_continuous_run

    def config_checker_job(self):
        """A very special job checking config for recent changes"""
        new_config = ConfigManager(CONFIG_PATH, CONFIG_OVERRIDE_PATH).load_config_with_override()

        # If anything at all changed in config
        # TODO: can be more precise here
        diff = DeepDiff(self.config, new_config)
        if diff:
            logger.info(f'Config was changed, diff: {diff}')
            self.reschedule_jobs(new_config)
        else:
            logger.info('No config changes detected')

    def init_jobs(self):
        logger.info('Starting setting job schedules...')
        for job_id, schedule_dict in self.config['jobs'].items():
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
                scheduled.do(
                    job, app_context=self.app_context, sender=self.sender
                ).tag(CUSTOM_JOB_TAG)
            except Exception as e:
                logger.error(f'Failed to schedule job {job_id} with params {schedule_dict}: {e}')
        logger.info('Finished setting jobs')

    def reschedule_jobs(self, new_config: dict):
        logger.info('Clearing all scheduled jobs...')
        schedule.clear(CUSTOM_JOB_TAG)  # clear only jobs originating from config
        ConfigManager.join_configs(self.config, new_config) # join in place to config object
        self.init_jobs()

    def stop_running(self):
        '''Set a stopping event so we can finish last job gracefully'''
        logger.info('Scheduler received a signal. Will terminate after ongoing jobs end')
        self.stop_run_event.set()
