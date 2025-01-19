import asyncio
import html
import logging
import threading
import time
from typing import List

import schedule
import telegram

from .app_context import AppContext
from .config_manager import ConfigManager
from .consts import AT, CONFIG_RELOAD_MINUTES, EVERY, KWARGS, SEND_TO, WEEKDAYS_SHORT
from .jobs.utils import get_job_runnable
from .strings import load
from .tg.sender import TelegramSender
from .utils.singleton import Singleton

logger = logging.getLogger(__name__)

CUSTOM_JOB_TAG = "custom"
TECHNICAL_JOB_TAG = "technical"


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

    def run(self):
        logger.info("Starting JobScheduler...")
        self.app_context = AppContext()
        self.telegram_sender = TelegramSender()
        schedule.every(CONFIG_RELOAD_MINUTES).minutes.do(
            get_job_runnable("config_updater_job"), self.app_context
        ).tag(TECHNICAL_JOB_TAG)

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
        logger.info("JobScheduler successfully initialized")

    def init_jobs(self):
        """
        Initializing jobs on latest config state.
        """
        logger.info("Starting setting job schedules...")
        jobs_config = self.config_manager.get_jobs_config()
        logger.info("Got jobs config")
        for job_id, schedules in jobs_config.items():
            logger.info(f'Found job "{job_id}"')
            if isinstance(schedules, dict):
                schedules = [schedules]
            for schedule_dict in schedules:
                try:
                    # E.g. ['minute'], ['sunday'] or ['10', 'minutes']
                    every_param = schedule_dict[EVERY].strip().split()
                    assert 1 <= len(every_param) <= 2
                    if len(every_param) == 2:
                        multiplier, time_unit = every_param
                        multiplier = int(multiplier)
                        assert 0 < multiplier
                        # e.g. schedule.every(10).minutes
                        scheduled = getattr(schedule.every(multiplier), time_unit)
                    else:
                        # e.g. schedule.every().hour
                        scheduled = getattr(schedule.every(), every_param[0])
                    if AT in schedule_dict:
                        # can't set "every 10 minutes" and "at 10:00" at the same time
                        assert len(every_param) < 2
                        # e.g. schedule.every().wednesday.at("10:00")
                        scheduled = scheduled.at(schedule_dict[AT], "Europe/Moscow")
                    scheduled.do(
                        get_job_runnable(job_id),
                        app_context=self.app_context,
                        send=self.telegram_sender.create_chat_ids_send(
                            schedule_dict.get(SEND_TO, [])
                        ),
                        kwargs=schedule_dict.get(KWARGS),
                    ).tag(CUSTOM_JOB_TAG)
                except Exception as e:
                    logger.error(
                        f"Failed to schedule job {job_id} with params {schedule_dict}: {e}"
                    )
        logger.info("Finished setting jobs")

    @staticmethod
    def _describe_job(job: schedule.Job, bot) -> str:
        # copied from schedule module
        if hasattr(job.job_func, "__name__"):
            job_func_name = job.job_func.__name__  # type: ignore
        else:
            job_func_name = repr(job.job_func)

        send_func = job.job_func.keywords.get("send", None)
        loop = asyncio.get_event_loop()
        recipient_links = []
        if send_func:
            for chat_id in send_func.chat_ids:
                try:
                    chat = loop.run_until_complete(
                        bot.get_chat(chat_id)
                    )
                    chat_name = chat.title or chat.username or str(chat_id)
                    recipient_links.append(
                        f'<a href="https://web.telegram.org/a/#{chat_id}">{chat_name}</a>'
                    )
                except telegram.error.BadRequest:
                    recipient_links.append(
                        f'<a href="https://web.telegram.org/a/#{chat_id}">{chat_id} (bad ID!)</a>'
                    )

        recipients = ', '.join(recipient_links)

        if job_func_name == 'SendRemindersJob':
            reminders = AppContext().db_client.get_reminders_by_user_id(None)
            reminder_descriptions = [
                load(
                    'jobs__reminder_job_reminder',
                    reminder_title=reminder.name,
                    reminder_interval=WEEKDAYS_SHORT[int(reminder.weekday)],
                    reminder_time=reminder.time,
                    recipients=f'<a href="https://web.telegram.org/a/#{chat.id}">{chat.title}</a>'
                ) for (reminder, chat) in reminders
            ]
            return load(
                'jobs__reminder_job_description',
                job_name=job_func_name,
                reminders_list='\n'.join(reminder_descriptions)
            )

        if job_func_name == 'SheetReportJob':
            job_func_name = f'{job_func_name} {job.job_func.keywords.get(KWARGS, {}).get("name")}'

        if job_func_name == 'TrelloBoardStateNotificationsJob':
            recipients = 'curators'

        return load(
            "jobs__job_description",
            job_name=job_func_name,
            job_time=job.at_time,
            job_interval=job.start_day or f'{job.interval} {job.unit}',
            recipients=recipients,
        )

    @staticmethod
    def list_jobs(bot) -> List[str]:
        return [JobScheduler._describe_job(job, bot) for job in schedule.jobs]

    def reschedule_jobs(self):
        logger.info("Clearing all scheduled jobs...")
        # clear only jobs originating from config
        schedule.clear(CUSTOM_JOB_TAG)
        self.config = self.config_manager.get_latest_config()
        self.init_jobs()

    def stop_running(self):
        """Set a stopping event so we can finish last job gracefully"""
        logger.info(
            ("Scheduler received a signal. " "Will terminate after ongoing jobs end")
        )
        self.stop_run_event.set()

    @staticmethod
    def _get_job_runnable(job_module):
        """
        Hack to add readable name for execute method for introspection.
        May be once replaced by Job base class.
        """
        execute_job = job_module.execute
        execute_job.__name__ = job_module.__name__
        return execute_job
