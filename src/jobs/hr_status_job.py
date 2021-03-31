from datetime import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..sheets.sheets_objects import HRPersonProcessed
from ..strings import load
from .base_job import BaseJob

from .utils import pretty_send

logger = logging.getLogger(__name__)


class HRStatusJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        paragraphs = [load('hr_status_job__header', date=datetime.today().strftime('%d.%m'))]
        people = HRStatusJob._get_people(app_context)
        people_new = list(filter(
            lambda p: p.status == load('sheets__hr__processed__status__new_form'),
            people
        ))
        logger.info(f'Found {len(people_new)} new people')
        paragraphs.append(load('hr_status_job__new_members_title'))
        for item in people_new:
            paragraphs.append(
                load(
                    'hr_status_job__new_member',
                    member_name=item.name,
                    member_tg=item.telegram or '',
                    date_submitted=item.date_submitted,
                    status=item.status_novice,
                    hr_name=item.hr_name,
                    interests=item.interests,
                    about_me=item.about,
                    contacts=item.other_contacts,
                )
            )

        people_trial = list(filter(
            lambda p: p.status == load('sheets__hr__processed__status__trial'),
            people
        ))
        logger.info(f'Found {len(people_trial)} people on trial')
        paragraphs.append(load('hr_status_job__trial_members_title'))
        for item in people_trial:
            curator = app_context.db_client.get_curator_by_role(item.curator)
            person_paragraph = load(
                'hr_status_job__trial_member',
                member_name=item.name,
                member_tg=item.telegram if item.telegram and item.telegram != "#N/A" else '',
                date_submitted=item.date_submitted,
                curator_name=curator.name if curator else item.curator,
                curator_tg=curator.telegram if curator else '',
            )
            if not item.telegram or item.telegram == "#N/A":
                person_paragraph += '\n' + load(
                    'hr_status_job__other_contacts',
                    contacts=item.other_contacts
                )
            paragraphs.append(person_paragraph)

        paragraphs.append(load('hr_status_job__footer'))
        pretty_send(paragraphs, send)

    @staticmethod
    def _get_people(app_context: AppContext) -> List[HRPersonProcessed]:
        return [
            HRPersonProcessed(item) for item
            in app_context.sheets_client.fetch_hr_forms_processed()
        ]
