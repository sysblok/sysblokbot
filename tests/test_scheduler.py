import pytest

from src import jobs
from src import scheduler
from src.bot import SysBlokBot
from src.config_manager import ConfigManager


# TODO: move to tests/fakes
class FakeTelegramSender:
    def send_to_managers(self, *args, **kwargs):
        pass

    def create_chat_ids_send(self, *args, **kwargs):
        pass

    def create_reply_send(self, *args, **kwargs):
        pass


class FakeJob:
    def execute(self, *args, **kwargs):
        pass


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
        setattr(jobs, job_id, FakeJob)

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
