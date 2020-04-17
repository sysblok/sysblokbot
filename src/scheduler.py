import logging
import schedule
import telegram

from .jobs import jobs


logger = logging.getLogger(__name__)


class JobScheduler:
    def __init__(self, config: dict, bot):
        self.config = config
        self.bot = bot

    def init_jobs(self):
        for job_id, schedule_dict in self.config['jobs'].items():
            try:
                job = getattr(jobs, job_id)
            except Exception as e:
                logger.error(f'Job {job_id} not found: {e}')
                continue
            try:
                scheduled = getattr(schedule.every(), schedule_dict['every'])
                if 'at' in schedule_dict:
                    scheduled = scheduled.at(schedule_dict['at'])
                scheduled.do(job, bot=self.bot)
            except Exception as e:
                logger.error(f'Failed to schedule job {job_id} with params {schedule_dict}: {e}')
