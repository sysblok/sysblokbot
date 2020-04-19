import pytest

from src import scheduler
from src.jobs import jobs
from src.bot import SysBlokBot


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
def test_scheduler(monkeypatch, jobs_config, num_jobs):
    for job_id in jobs_config:
        setattr(jobs, job_id, lambda _: 0)

    scheduler.schedule.clear()
    job_scheduler = scheduler.JobScheduler({'jobs': jobs_config})
    # Instead of: job_scheduler.run(sysblok_bot=None)
    job_scheduler.app_context = None
    job_scheduler.sender = None

    job_scheduler.init_jobs()
    assert len(scheduler.schedule.jobs) == num_jobs + 1
