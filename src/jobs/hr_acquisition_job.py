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
        old_people = [person for person in people if person.status != '']
        new_people = [person for person in people if person.status == '']
        for person in new_people:
            if person.telegram == '' and person.other_contacts == '':
                person.item.set_field_value(load('sheets__hr__status'), 'Отказ')
                continue
            if person.telegram != '' and person.telegram in {
                person.telegram for person in old_people
            }:
                person.item.set_field_value(load('sheets__hr__status'), 'Дубль')
                continue

