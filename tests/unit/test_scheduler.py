import logging

import pytest
import schedule
from fakes import fake_job
from freezegun import freeze_time

from src import jobs, scheduler

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
    ],
)
def test_jobs_scheduled(jobs_config, num_jobs, mock_config_jobs_manager, mock_sender):
    for job_id in jobs_config:
        setattr(jobs, job_id, fake_job)

    mock_config_jobs_manager._latest_jobs_config = jobs_config

    scheduler.schedule.clear()

    # create singleton instance from scratch
    scheduler.JobScheduler.drop_instance()
    job_scheduler = scheduler.JobScheduler()
    job_scheduler.app_context = None
    job_scheduler.telegram_sender = mock_sender
    job_scheduler.init_jobs()

    assert len(scheduler.schedule.jobs) == num_jobs


def test_jobs_executed(mock_config_jobs_manager, mock_sender):
    setattr(jobs, "job", fake_job)

    mock_config_jobs_manager._latest_jobs_config = {
        "job": {"every": "day", "at": "12:00"}
    }

    scheduler.schedule.clear()
    fake_job.reset_run_counter()

    # create singleton instance from scratch
    scheduler.JobScheduler.drop_instance()
    job_scheduler = scheduler.JobScheduler()
    job_scheduler.app_context = None
    job_scheduler.telegram_sender = mock_sender

    with freeze_time("2020-05-01 11:59:00"):
        job_scheduler.init_jobs()
    with freeze_time("2020-05-01 12:00:50"):
        schedule.run_pending()

    assert fake_job.run_counter == 1
