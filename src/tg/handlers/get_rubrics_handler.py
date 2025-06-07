import logging
from typing import List

import telegram
from telegram import Update
from telegram.ext import CallbackContext

from ... import consts
from ...app_context import AppContext
from ...consts import PlainTextUserAction
from .utils import manager_only, reply

logger = logging.getLogger(__name__)

EXCLUDED_RUBRICS = {
    "возвращено на доработку",
    "есть иллюстрация",
    "предложено на иллюстрацию",
    "телеграм",
}

TASK_NAME = "get_rubrics"


@manager_only
def get_rubrics(update: Update, tg_context: CallbackContext) -> None:
    logger.info("get_rubrics: start")
    app_context = AppContext()

    try:
        labels = app_context.focalboard_client._get_labels()
        filtered = [
            lbl.name
            for lbl in labels
            if lbl.name and lbl.name.lower() not in EXCLUDED_RUBRICS
        ]
        filtered.sort()
        logger.info("get_rubrics: %d rubrics after filter", len(filtered))

        if not filtered:
            reply("Рубрики не найдены.", update)
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
        reply(
            "Пожалуйста, пришли номер рубрики, с которой хочешь работать:\n\n"
            + rubric_list,
            update,
        )
        logger.info("get_rubrics: sent rubric list to user")

    except Exception as e:
        logger.error("get_rubrics: error %s", e, exc_info=True)
        reply("Не удалось получить список рубрик. Попробуй позже.", update)
