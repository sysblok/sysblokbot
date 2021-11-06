import logging
from typing import Callable, List
import re

from ..app_context import AppContext
from ..strings import load
from .base_job import BaseJob

from .utils import pretty_send

logger = logging.getLogger(__name__)

class PostcardsReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        spreadsheet_key = app_context.config_manager.get_sheets_config()['postcards_sheet_key']
        sheet = app_context.sheets_client.fetch_sheet(spreadsheet_key, 'New_Статистика')
        message_template = load('postcard_report_job__message')
        message_template_substituted = message_template
        # looking for all placeholders in format [[A1]] and substituting them
        for element in re.findall(r'(\[\[[a-zA-Z]+[0-9]+\]\])', message_template):
            cell_range = sheet.get_range_from_a1(element[2:-2])
            value = str(cell_range.get_values()[0][0])
            message_template_substituted = message_template_substituted.replace(element, value)
        pretty_send([message_template_substituted], send)
