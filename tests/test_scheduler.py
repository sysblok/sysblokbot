import datetime
import logging
import pytest
import time

from freezegun import freeze_time
import schedule

from src import jobs
from src import scheduler
from src.bot import SysBlokBot
from src.config_manager import ConfigManager

from fakes import fake_job
from fakes.fake_sender import FakeTelegramSender


logger = logging.getLogger(__name__)


@pytest.mark.parametrize(
    "jobs_config, num_jobs",
    [
        ({"job": {"every": "day"}}, 1),
        ({"job": {"every": "day", "at": "10:00"}}, 1),
        ({"job": {"every": "monday", "at": "10:00"}}, 1),
        ({"job": {"every": "tuesday", "at": "10:00"}}, 1),
        ({"job": {"every": "wednesday", "at": "10:00"}}, 1),
        ({"job": {"every": "thursday", "at": "10:00"}}, 1),
        ({"job": {"every": "friday", "at": "10:00"}}, 1),
        ({"job": {"every": "saturday", "at": "10:00"}}, 1),
        ({"job": {"every": "sunday", "at": "10:00"}}, 1),
        ({"job": {"every": "hour"}}, 1),
        ({"job": {"every": "day", "at": "10"}}, 0),
    ]
)
def test_jobs_scheduled(jobs_config, num_jobs):
    for job_id in jobs_config:
        setattr(jobs, job_id, fake_job)

    config_manager = ConfigManager()
    config_manager._latest_config = {'jobs': jobs_config}

    scheduler.schedule.clear()

    # create singleton instance from scratch
    scheduler.JobScheduler.drop_instance()
    job_scheduler = scheduler.JobScheduler()
    job_scheduler.app_context = None
    job_scheduler.telegram_sender = FakeTelegramSender()
    job_scheduler.init_jobs()

    assert len(scheduler.schedule.jobs) == num_jobs


def test_jobs_executed():
    setattr(jobs, "job", fake_job)

    config_manager = ConfigManager()
    config_manager._latest_config = {'jobs': {"job": {"every": "day", "at": "12:00"}}}

    scheduler.schedule.clear()
    fake_job.reset_run_counter()

    # create singleton instance from scratch
    scheduler.JobScheduler.drop_instance()
    job_scheduler = scheduler.JobScheduler()
    job_scheduler.app_context = None
    job_scheduler.telegram_sender = FakeTelegramSender()

    with freeze_time("2020-05-01 11:59:00"):
        job_scheduler.init_jobs()
    with freeze_time("2020-05-01 12:00:50"):
        schedule.run_pending()

    assert fake_job.run_counter == 1
