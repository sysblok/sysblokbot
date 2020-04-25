import logging
import time
import threading

from deepdiff import DeepDiff
import schedule
import telegram

from . import consts
from .bot import SysBlokBot
from .config_manager import ConfigManager
from .jobs import jobs
from .tg.sender import TelegramSender


logger = logging.getLogger(__name__)

CUSTOM_JOB_TAG = "custom"
TECHNICAL_JOB_TAG = "technical"


class JobScheduler:
    """
    Don't forget to call run() after initializing.
    """

    def __init__(self, config: dict):
        logger.info("Creating JobScheduler instance")
        self.config = config
        # re-read config
        schedule.every(15).minutes.do(self.config_checker_job).tag(TECHNICAL_JOB_TAG)

    def run(self, sysblok_bot: SysBlokBot):
        logger.info("Starting JobScheduler...")
        self.app_context = sysblok_bot.app_context
        self.sender = TelegramSender(
            sysblok_bot.dp.bot, self.config[consts.TELEGRAM_CONFIG]
        )

        cease_continuous_run = threading.Event()

        class ScheduleThread(threading.Thread):
            @classmethod
            def run(cls):
                while not cease_continuous_run.is_set():
                    try:
                        schedule.run_pending()
                    except Exception as e:
                        logger.error(f"Error while running scheduled jobs: {e}")
                    time.sleep(1)
                return cease_continuous_run

        continuous_thread = ScheduleThread()
        continuous_thread.start()
        self.stop_run_event = cease_continuous_run

    def config_checker_job(self):
        """A very special job checking config for recent changes"""
        new_config = ConfigManager(
            consts.CONFIG_PATH, consts.CONFIG_OVERRIDE_PATH
        ).load_config_with_override()

        # If anything at all changed in config
        # TODO: can be more precise here
        diff = DeepDiff(self.config, new_config)
        if diff:
            logger.info(f"Config was changed, diff: {diff}")
            # update config['jobs']
            self.reschedule_jobs(new_config)
            # update config['telegram']
            self.sender.update_config(new_config[consts.TELEGRAM_CONFIG])
            # update config['trello']
            self.app_context.trello_client.update_config(
                new_config[consts.TRELLO_CONFIG]
            )
        else:
            logger.info("No config changes detected")

    def init_jobs(self):
        logger.info("Starting setting job schedules...")
        for job_id, schedule_dict in self.config["jobs"].items():
            try:
                job = getattr(jobs, job_id)
            except Exception as e:
                logger.error(f'Job "{job_id}" not found: {e}')
                continue
            logger.info(f'Found job "{job_id}"')
            try:
                scheduled = getattr(schedule.every(), schedule_dict["every"])
                if "at" in schedule_dict:
                    scheduled = scheduled.at(schedule_dict["at"])
                scheduled.do(job, app_context=self.app_context, sender=self.sender).tag(
                    CUSTOM_JOB_TAG
                )
            except Exception as e:
                logger.error(
                    f"Failed to schedule job {job_id} \
                    with params {schedule_dict}: {e}"
                )
        logger.info("Finished setting jobs")

    def reschedule_jobs(self, new_config: dict):
        logger.info("Clearing all scheduled jobs...")
        # clear only jobs originating from config
        schedule.clear(CUSTOM_JOB_TAG)
        # join in place to config object
        ConfigManager.join_configs(self.config, new_config)
        self.init_jobs()

    def stop_running(self):
        """Set a stopping event so we can finish last job gracefully"""
        logger.info(
            "Scheduler received a signal. \
            Will terminate after ongoing jobs end"
        )
        self.stop_run_event.set()
