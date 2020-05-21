import datetime
import json
import logging
from typing import Callable, List

from deepdiff import DeepDiff

from ..app_context import AppContext
from ..scheduler import JobScheduler
from ..tg.sender import TelegramSender
from ..trello.trello_client import TrelloClient
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class DBFetchAuthorsSheetJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        num_authors = app_context.db_client.fetch_authors_sheet(app_context.sheets_client)
        logger.info(f'Fetched {num_authors} authors')
        send(f'Fetched {num_authors} authors')
