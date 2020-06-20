import logging
from typing import Callable

from ..app_context import AppContext
from .base_job import BaseJob

logger = logging.getLogger(__name__)


# TODO: merge with fetch authors job
class DBFetchCuratorsSheetJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        num_authors = app_context.db_client.fetch_curators_sheet(app_context.sheets_client)
        logger.info(f'Fetched {num_authors} curators')
        send(f'Fetched {num_authors} curators')
