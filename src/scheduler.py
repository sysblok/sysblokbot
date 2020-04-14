import schedule
import telegram

from .jobs import jobs


class JobScheduler:
    def __init__(self, config: dict, trello_client, sheets_client, telegram_sender):
        self.config = config
        self.telegram_sender = telegram_sender
        self.trello_client = trello_client
        self.sheets_client = sheets_client

    def init_jobs(self):
        # TODO: parse config for scheduled time
        schedule.every().wednesday.at("13:15").do(
            jobs.sample_job,
            trello_client=self.trello_client,
            sheets_client=self.sheets_client,
            telegram_sender=self.telegram_sender
        )

