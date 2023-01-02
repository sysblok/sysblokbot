import logging
from typing import Callable

from ..app_context import AppContext
from ..strings import load
from .base_job import BaseJob

logger = logging.getLogger(__name__)


# TODO: merge with fetch authors job
class DBFetchCuratorsSheetJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        num_curators = app_context.db_client.fetch_curators_sheet(
            app_context.sheets_client
        )
        logger.info(f"Fetched {num_curators} curators")
        send(load("db_fetch_curators_sheet_job__success", num_curators=num_curators))
