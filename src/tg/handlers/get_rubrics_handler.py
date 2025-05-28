# import logging
# import telegram
# from telegram import Update
# from telegram.ext import CallbackContext

# from ... import consts
# from ...app_context import AppContext
# from ...consts import PlainTextUserAction
# from .utils import manager_only, reply

# logger = logging.getLogger(__name__)

# EXCLUDED_RUBRICS = {
#     "возвращено на доработку",
#     "есть иллюстрация",
#     "предложено на иллюстрацию",
#     "телеграм",
# }

# TASK_NAME = "get_rubrics"


# @manager_only
# def get_rubrics(update: Update, tg_context: CallbackContext):
#     """
#     Шаг 1: команда /get_rubrics — запрашиваем рубрики из Focalboard,
#     отправляем пользователю пронумерованный список и ждём ввода номера.
#     """
#     app_context = AppContext()
#     command_data = {}

#     try:
#         labels = app_context.focalboard_client._get_labels()
#         # фильтрация
#         filtered_labels = [
#             lbl.name
#             for lbl in labels
#             if lbl.name and lbl.name.lower() not in EXCLUDED_RUBRICS
#         ]
#         sorted_labels = sorted(filtered_labels)

#         if not sorted_labels:
#             reply("Рубрики не найдены.", update)
#             return

#         # готовим сообщение с пронумерованным списком
#         rubric_list = "\n".join(f"{i+1}) {name}" for i,
#                                 name in enumerate(sorted_labels))
#         reply(
#             "Пожалуйста, пришли номер рубрики, с которой хочешь работать:\n\n"
#             + rubric_list,
#             update
#         )

#         # сохраняем состояние
#         command_data[consts.GetTasksReportData.LISTS] = sorted_labels
#         command_data[consts.NEXT_ACTION] = PlainTextUserAction.GET_RUBRICS__CHOOSE_RUBRIC.value
#         tg_context.chat_data[TASK_NAME] = command_data
#         tg_context.chat_data[consts.LAST_ACTIONABLE_COMMAND] = TASK_NAME

#     except Exception as e:
#         logger.error(f"Error fetching rubrics: {e}", exc_info=True)
#         reply("Произошла ошибка при получении рубрик. Попробуй позже.", update)


# @manager_only
# def handle_user_message(update: Update, tg_context: CallbackContext, button=None):
#     """
#     Шаг 2: ловим любой текст — если мы ожидаем номер рубрики,
#     парсим его, отвечаем и завершаем сценарий.
#     """
#     # проверяем, что это нужный сценарий
#     if tg_context.chat_data.get(consts.LAST_ACTIONABLE_COMMAND) != TASK_NAME:
#         return

#     command_data = tg_context.chat_data.get(TASK_NAME, {})
#     if command_data.get(consts.NEXT_ACTION) != PlainTextUserAction.GET_RUBRICS__CHOOSE_RUBRIC.value:
#         return

#     # вход от пользователя
#     user_text = update.message.text.strip() if update.message else ""
#     rubrics = command_data.get(consts.GetTasksReportData.LISTS, [])

#     # пытаемся распарсить номер
#     try:
#         idx = int(user_text) - 1
#     except ValueError:
#         reply("Пожалуйста, введи корректный номер рубрики.", update)
#         return

#     # проверяем диапазон
#     if 0 <= idx < len(rubrics):
#         chosen = rubrics[idx]
#         reply(f"Ты выбрал рубрику: {chosen}", update)
#         # завершаем сценарий
#         command_data[consts.NEXT_ACTION] = None
#         tg_context.chat_data[TASK_NAME] = command_data
#         tg_context.chat_data.pop(consts.LAST_ACTIONABLE_COMMAND, None)
#     else:
#         reply(
#             f"Номер введён неправильно. Пришли от 1 до {len(rubrics)}.", update)
#         # NEXT_ACTION остаётся прежним, пользователь может ввести ещё раз


# import logging
# from typing import List

# import telegram
# from telegram import Update
# from telegram.ext import CallbackContext

# from ... import consts
# from ...app_context import AppContext
# from ...consts import PlainTextUserAction
# from .utils import manager_only, reply

# logger = logging.getLogger(__name__)

# # Метки, которые не считаем полноценными «рубриками»
# EXCLUDED_RUBRICS = {
#     "возвращено на доработку",
#     "есть иллюстрация",
#     "предложено на иллюстрацию",
#     "телеграм",
# }

# TASK_NAME = "get_rubrics"


# @manager_only
# def get_rubrics(update: Update, tg_context: CallbackContext) -> None:
#     """
#     /get_rubrics → показываем список рубрик с номерами,
#     сохраняем состояние и ждём обычного текста от пользователя.
#     """
#     app_context = AppContext()

#     try:
#         # все labels из Focalboard
#         labels = app_context.focalboard_client._get_labels()

#         filtered: List[str] = [
#             lbl.name
#             for lbl in labels
#             if lbl.name and lbl.name.lower() not in EXCLUDED_RUBRICS
#         ]
#         filtered.sort()

#         if not filtered:
#             reply("Рубрики не найдены.", update)
#             return

#         rubric_list = "\n".join(f"{i + 1}) {name}" for i,
#                                 name in enumerate(filtered))
#         reply(
#             "Пожалуйста, пришли номер рубрики, с которой хочешь работать:\n\n"
#             + rubric_list,
#             update,
#         )

#         # сохраняем данные в chat_data, чтобы использовать на следующем шаге
#         tg_context.chat_data[TASK_NAME] = {
#             consts.GetTasksReportData.LISTS: filtered,
#         }
#         tg_context.chat_data[consts.NEXT_ACTION] = PlainTextUserAction.GET_RUBRICS__CHOOSE_RUBRIC
#         tg_context.chat_data[consts.LAST_ACTIONABLE_COMMAND] = TASK_NAME

#     except Exception as e:
#         logger.error("get_rubrics: %s", e, exc_info=True)
#         reply("Не удалось получить список рубрик. Попробуй позже.", update)


# def handle_choose_rubric(update: Update, tg_context: CallbackContext) -> None:
#     """
#     Шаг 2: получаем номер рубрики от пользователя, отвечаем «Ура!» или ошибкой.
#     """
#     user_input = update.message.text.strip()
#     rubrics = tg_context.chat_data.get(TASK_NAME, {}).get(
#         consts.GetTasksReportData.LISTS, [])

#     try:
#         idx = int(user_input) - 1
#         assert 0 <= idx < len(rubrics)
#     except Exception:
#         reply("Пожалуйста, введи корректный номер рубрики.", update)
#         return

#     reply(f"Ура! Ты выбрал рубрику: {rubrics[idx]}", update)
#     # Сброс состояния
#     tg_context.chat_data.pop(consts.NEXT_ACTION, None)
#     tg_context.chat_data.pop(consts.LAST_ACTIONABLE_COMMAND, None)
#     tg_context.chat_data.pop(TASK_NAME, None)

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
