import schedule

from .jobs import jobs
from .tg_sender.sender import TelegramSender
from .sheets.sheets_client import GoogleSheetsClient
from .trello.trello_client import TrelloClient

class JobScheduler:
    def __init__(self, config: dict):
        self.config = config
        self.telegram_sender = TelegramSender()
        self.trello_client = TrelloClient(
            config=config['trello']
        )
        self.sheets_client = GoogleSheetsClient(
            api_key=config['sheets']['api_key']
        )

    def init_jobs(self):
        # TODO: parse config for scheduled time
        schedule.every().wednesday.at("13:15").do(
            jobs.sample_job,
            trello_client=self.trello_client,
            sheets_client=self.sheets_client,
            telegram_sender=self.telegram_sender
        )

