import logging
import schedule
import telegram

from .jobs import jobs


logger = logging.getLogger(__name__)


class JobScheduler:
    def __init__(self, config: dict, trello_client, sheets_client, telegram_sender):
        self.config = config
        self.telegram_sender = telegram_sender
        self.trello_client = trello_client
        self.sheets_client = sheets_client

    def init_jobs(self):
        for job_id, schedule_dict in self.config['jobs'].items():
            try:
                job = getattr(jobs, job_id)
            except Exception as e:
                logger.error(f'Job {job_id} not found: {e}')
                continue
            try:
                if 'at' in schedule_dict:
                    getattr(schedule.every(), schedule_dict['every']).at(schedule_dict['at']).do(
                        job,
                        trello_client=self.trello_client,
                        sheets_client=self.sheets_client,
                        telegram_sender=self.telegram_sender
                    )
                else:
                    getattr(schedule.every(), schedule_dict['every']).do(
                        job,
                        trello_client=self.trello_client,
                        sheets_client=self.sheets_client,
                        telegram_sender=self.telegram_sender
                    )
            except Exception as e:
                logger.error(f'Failed to schedule job {job_id} with params {schedule_dict}: {e}')
