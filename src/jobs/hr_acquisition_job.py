import logging
from sheetfu import Table
from typing import Callable, List

from ..app_context import AppContext
from ..sheets.sheets_objects import HRPersonRaw, HRPersonProcessed
from ..strings import load
from ..tg.sender import pretty_send
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class HRAcquisitionJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        paragraphs = [load("hr_acquisition_job__hello")]  # list of paragraph strings

        new_people = HRAcquisitionJob._process_new_people(app_context)

        if not new_people:
            return

        paragraphs += [
            HRAcquisitionJob._get_new_person_paragraph(item) for item in new_people
        ]

        pretty_send(paragraphs, send)

    @staticmethod
    def _process_new_people(
        app_context: AppContext,
    ) -> List[HRPersonProcessed]:
        forms_raw = app_context.sheets_client.fetch_hr_forms_raw()
        forms_processed = app_context.sheets_client.fetch_hr_forms_processed()

        new_items = HRAcquisitionJob._process_raw_forms(forms_raw, forms_processed)

        try:
            forms_raw.commit()
            forms_processed.commit()
        except Exception as e:
            logger.error(f"failed to export data: {e}")

        return new_items

    @staticmethod
    def _process_raw_forms(
        forms_raw: Table, forms_processed: Table
    ) -> List[HRPersonProcessed]:
        people = [HRPersonRaw(item) for item in forms_raw]
        existing_people = [person for person in people if person.status]
        new_people = [person for person in people if not person.status]
        new_items = []

        for person in new_people:
            # filter out incomplete responses
            if not person.telegram and not person.other_contacts:
                person.status = load("sheets__hr__raw__status_rejection")
                continue
            if person.telegram and (
                person.telegram in {person.telegram for person in existing_people}
                or person.telegram in {person.telegram for person in new_items}
            ):
                person.status = load("sheets__hr__raw__status_double")
                continue

            # move good ones to another sheet
            person.status = load("sheets__hr__raw__status_processed")
            # TODO: PR to sheetfu which will allow better API here
            person_dict = {
                "id": len(forms_processed)
                + 2,  # 1 for starting with 1 and 1 for the header
                "name": person.name,
                "interests": person.interests,
                "other_contacts": person.other_contacts,
                "about": person.about,
                "date_submitted": person.ts,
                "telegram": person.telegram,
                "status": load("sheets__hr__processed__status__new_form"),
                "source": load("sheets__hr__processed__source__form"),
            }
            new_items.append(
                HRPersonProcessed.add_one_to_table(forms_processed, person_dict)
            )

        return new_items

    @staticmethod
    def _get_new_person_paragraph(item: HRPersonProcessed) -> str:
        name = load(
            "hr_acquisition_job__name",
            name=item.name,
            telegram=item.telegram,
            date=item.date_submitted.split(" ")[0],
        )
        interests = load("hr_acquisition_job__interests", interests=item.interests)
        about = load("hr_acquisition_job__about", description=item.about)
        other_contacts = load(
            "hr_acquisition_job__other_contacts", contacts=item.other_contacts
        )
        paragraph = load(
            "hr_acquisition_job__person",
            name=name,
            interests=interests,
            about=about,
            contacts=other_contacts,
        )
        return paragraph
