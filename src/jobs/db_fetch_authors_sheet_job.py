import logging
from typing import Callable

from ..app_context import AppContext
from ..strings import load
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class DBFetchAuthorsSheetJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        num_authors = app_context.db_client.fetch_authors_sheet(
            app_context.sheets_client
        )
        logger.info(f"Fetched {num_authors} authors")
        send(load("db_fetch_authors_sheet_job__success", num_authors=num_authors))
