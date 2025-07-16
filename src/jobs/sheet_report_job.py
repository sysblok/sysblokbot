import logging
import re
import time
from datetime import datetime
from typing import Callable

from sheetfu.exceptions import SheetNameNoMatchError

from ..app_context import AppContext
from ..consts import KWARGS
from ..strings import load
from ..tg.sender import pretty_send
from .base_job import BaseJob

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
        *args,
        **kwargs,
    ):
        logger.info(f"Getting sheet report for: {kwargs.get('name')}")
        if called_from_handler:
            # TODO: refactor and move it to helper
            schedules = app_context.config_manager.get_jobs_config(
                __name__.split(".")[-1]
            )
            if len(args) == 0:
                names = [schedule.get(KWARGS, {}).get("name") for schedule in schedules]
                send(f"Usage: /get_report_from_sheet name\nAvailable names: {names}")
                return
            assert len(args) == 1
            name = args[0]
            for schedule in schedules:
                if schedule.get(KWARGS, {}).get("name") == name:
                    kwargs = schedule[KWARGS]
        spreadsheet_key = kwargs["spreadsheet_key"]
        sheet_name = kwargs.get("sheet_name")
        message_template = load(
            kwargs["template_string"],
            date=datetime.now().strftime("%d.%m.%Y"),
            url=f"https://docs.google.com/spreadsheets/d/{spreadsheet_key}",
        )
        try:
            sheet = app_context.sheets_client.fetch_sheet(spreadsheet_key, sheet_name)
        except SheetNameNoMatchError:
            raise KeyError(f"sheet_report_job can't find sheet '{sheet_name}'")
        message_template_substituted = message_template
        # looking for all placeholders in format [[A1]] and substituting them
        for element in re.findall(r"(\[\[[a-zA-Z]+[0-9]+\]\])", message_template):
            cell_range = sheet.get_range_from_a1(element[2:-2])
            value = str(cell_range.get_values()[0][0])
            message_template_substituted = message_template_substituted.replace(
                element, value
            )
            time.sleep(2)
        pretty_send([message_template_substituted], send)
