import logging
from sheetfu import Table
from sheetfu.modules.table import Item
from typing import Callable, List

from ..app_context import AppContext
from ..sheets.sheets_objects import HRPersonRaw
from ..strings import load
from .base_job import BaseJob

from .utils import pretty_send

logger = logging.getLogger(__name__)

class HRAcquisitionJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = [load('hr_acquisition_job__hello')]  # list of paragraph strings
        errors = {}

        logger.warning(paragraphs)

        paragraphs.append(HRAcquisitionJob._get_new_people_paragraphs(app_context, errors))

        pretty_send(paragraphs, send)

    @staticmethod
    def _get_new_people_paragraphs(
            app_context: AppContext,
            errors: dict,
    ) -> List[str]:
        forms_raw = app_context.sheets_client.fetch_hr_forms_raw()
        forms_processed = app_context.sheets_client.fetch_hr_forms_processed()

        new_items = HRAcquisitionJob._process_raw_forms(forms_raw, forms_processed)

        forms_raw.commit()

    @staticmethod
    def _process_raw_forms(forms_raw: Table, forms_processed: Table) -> List[Item]:
        people = [HRPersonRaw(item) for item in forms_raw]
        existing_people = [person for person in people if person.status]
        new_people = [person for person in people if not person.status]

        for person in new_people:
            # filter out incomplete responses
            if not person.telegram and not person.other_contacts:
                person.status = 'Отказ'
                continue
            if person.telegram and person.telegram in {
                person.telegram for person in existing_people
            }:
                person.status = 'Дубль'
                continue
        
            # move good ones to another sheet

