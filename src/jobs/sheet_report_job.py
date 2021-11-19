import logging
from datetime import datetime
from typing import Callable, List
import re

from ..app_context import AppContext
from ..strings import load
from .base_job import BaseJob

from .utils import pretty_send

logger = logging.getLogger(__name__)


class SheetReportJob(BaseJob):
    """
    kwargs has to be set in job config.
    kwargs required: spreadsheet_key, template_string
    kwargs optional:
      - sheet_name (required if it's not the first tab)
      - name (for readability and logs)
    """
    @staticmethod
    def _execute(
            app_context: AppContext,
            send: Callable[[str], None],
            called_from_handler=False,
            **kwargs
    ):
        logger.info(f'Getting sheet report for: {kwargs.get("name")}')
        if called_from_handler:
            pretty_send(['TODO: debug mode not working yet'], send)
            return
        spreadsheet_key = kwargs['spreadsheet_key']
        sheet_name = kwargs.get('sheet_name')
        message_template = load(
            kwargs['template_string'],
            date=datetime.now().strftime('%d.%m.%Y')
        )
        sheet = app_context.sheets_client.fetch_sheet(spreadsheet_key, sheet_name)
        message_template_substituted = message_template
        # looking for all placeholders in format [[A1]] and substituting them
        for element in re.findall(r'(\[\[[a-zA-Z]+[0-9]+\]\])', message_template):
            cell_range = sheet.get_range_from_a1(element[2:-2])
            value = str(cell_range.get_values()[0][0])
            message_template_substituted = message_template_substituted.replace(element, value)
        pretty_send([message_template_substituted], send)
