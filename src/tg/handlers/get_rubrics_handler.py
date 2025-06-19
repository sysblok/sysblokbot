import logging
from typing import List

import telegram
from telegram import Update
from telegram.ext import CallbackContext

from src.strings import load

from ... import consts
from ...app_context import AppContext
from ...consts import PlainTextUserAction
from .utils import manager_only, reply

logger = logging.getLogger(__name__)

EXCLUDED_LOAD_KEYS = [
    "common_report__section_title_proofreading",
    "common_report_illustration",
    "common_report_proposed_illustration",
    "common_report_telegram",
]

TASK_NAME = "get_rubrics"


@manager_only
def get_rubrics(update: Update, tg_context: CallbackContext) -> None:
    logger.info("get_rubrics: start")
    app_context = AppContext()

    excluded_rubrics = {load(key) for key in EXCLUDED_LOAD_KEYS}
    try:
        labels = app_context.focalboard_client._get_labels()
        filtered = [
            lbl.name
            for lbl in labels
            if lbl.name and lbl.name.lower() not in excluded_rubrics
        ]
        filtered.sort()
        logger.info("get_rubrics: %d rubrics after filter", len(filtered))

        if not filtered:
            reply(load("rubrics_not_found"), update)
            return

        cmd_data = {
            consts.GetTasksReportData.LISTS: filtered,
            consts.NEXT_ACTION: PlainTextUserAction.GET_RUBRICS__CHOOSE_RUBRIC.value,
        }
        tg_context.chat_data[TASK_NAME] = cmd_data
        tg_context.chat_data[consts.LAST_ACTIONABLE_COMMAND] = TASK_NAME
        logger.info(
            "get_rubrics: saved command_data and LAST_ACTIONABLE_COMMAND=%s", TASK_NAME
        )

        # Show list
        rubric_list = "\n".join(f"{i + 1}) {name}" for i, name in enumerate(filtered))
        message = load("get_rubric_number") + "\n" + rubric_list
        reply(message, update)
        logger.info("get_rubrics: sent rubric list to user")

    except Exception as e:
        logger.error("get_rubrics: error %s", e, exc_info=True)
        reply(load("failed_get_rubrics_list"), update)
