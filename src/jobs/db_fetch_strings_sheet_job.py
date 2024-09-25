import logging
from typing import Callable

from ..app_context import AppContext
from ..strings import load
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class DBFetchStringsSheetJob(BaseJob):
    @staticmethod
    async def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        num_strings = app_context.strings_db_client.fetch_strings_sheet(
            app_context.sheets_client
        )
        logger.info(f"Fetched {num_strings} strings")
        await send(load("db_fetch_strings_sheet_job__success",
                   num_strings=num_strings))
