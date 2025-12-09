import calendar
import logging
import telegram
from datetime import datetime
from ... import consts
from ...app_context import AppContext
from ...consts import (
    ButtonValues,
    GetTasksReportData,
    PlainTextUserAction,
    BoardListAlias,
)
from ...db.db_client import DBClient
from ...db.db_objects import Reminder
from ...focalboard.focalboard_client import FocalboardClient
from ...strings import load
from ...tg.handlers import get_tasks_report_handler
from ...trello.trello_client import TrelloClient
from .utils import get_chat_id, get_chat_name, get_sender_id, reply

logger = logging.getLogger(__name__)

SECTIONS = [
    ("Идеи для статей", BoardListAlias.TOPIC_SUGGESTION_1),
    ("Готовая тема", BoardListAlias.TOPIC_READY_2),
    ("Уже пишу", BoardListAlias.DRAFT_N_PROGRESS_3, True),
    ("Передано на редактуру", BoardListAlias.DRAFT_COMPLETED_4),
    ("На редактуре", BoardListAlias.PENDING_EDITOR_5),
    ("Проверка качества SEO", BoardListAlias.PENDING_SEO_EDITOR_6),
    ("Отредактировано", BoardListAlias.APPROVED_EDITOR_7),
    ("Отобрано на финальную проверку", BoardListAlias.PENDING_CHIEF_EDITOR_8),
    ("Отобрано для публикации", BoardListAlias.PUBLISH_BACKLOG_9),
    ("Готово для вёрстки", BoardListAlias.PUBLISH_IN_PROGRESS_10),
]


def _generate_rubric_summary(update, rubric_name: str) -> None:
    try:
        app_context = AppContext()
        fc = app_context.focalboard_client
        labels = fc._get_labels()
        rubric_label = next(
            (
                lbl
                for lbl in labels
                if lbl.name.strip().lower() == rubric_name.strip().lower()
            ),
            None,
        )
        if not rubric_label:
            logger.warning(
                f"_generate_rubric_summary: Рубрика не найдена: {rubric_name}"
            )
            reply(
                load(
                    "rubric_not_found",
                    rubric_name=rubric_name,
                ),
            )
            return

        # Get all lists
        try:
            lists = fc.get_lists(board_id=fc.board_id, sorted=False)
        except Exception as e:
            logger.error(
                f"_generate_rubric_summary: не удалось получить lists: {e}",
                exc_info=True,
            )
            reply(load("failed_get_board_lists"), update)
            return

        message_parts = [
            load(
                "rubric_report_job__intro",
                rubric=rubric_name,
            )
        ]

        had_errors = False

        for column_name, alias, *meta_flag in SECTIONS:
            need_meta = bool(meta_flag and meta_flag[0])
            heading = load(alias.value)
            # Find column
            target_list = next(
                (lst for lst in lists if lst.name.strip().startswith(column_name)), None
            )

            if not target_list:
                message_parts.append(f"<b>{heading}</b> (0)")
                message_parts.append("")
                continue

            try:
                cards = fc.get_cards(list_ids=[target_list.id], board_id=fc.board_id)
            except Exception:
                had_errors = True
                message_parts.append(f"<b>{heading}</b> (0)")
                message_parts.append("")
                continue

            filtered = [
                card
                for card in cards
                if any(lbl.id == rubric_label.id for lbl in card.labels)
            ]

            filtered.sort(key=lambda c: c.due or datetime.max)

            count = len(filtered)
            message_parts.append(f"<b>{heading}</b> ({count})")

            if not filtered:
                message_parts.append("(пусто)")
            else:
                for card in filtered:
                    link = f'<a href="{card.url}">{card.name}</a>'
                    if need_meta:
                        due_str = (
                            card.due.strftime("%d.%m.%Y") if card.due else "без срока"
                        )
                        try:
                            fields = fc.get_custom_fields(card.id)
                            authors = (
                                ", ".join(fields.authors)
                                if fields.authors
                                else "неизвестно"
                            )
                        except Exception:
                            authors = "неизвестно"
                            message_parts.append(f"- {link}")
                            message_parts.append(f"  • Дедлайн: {due_str}")
                            message_parts.append(f"  • Автор: {authors}")
                    else:
                        message_parts.append(f"- {link}")

            message_parts.append("")

        if had_errors:
            message_parts.append(load("partial_data_error "))

        reply("\n".join(message_parts), update, parse_mode="HTML")

    except Exception:
        reply(load("failed_try_later"), update)


def handle_callback_query(
    update: telegram.Update, tg_context: telegram.ext.CallbackContext
):
    """
    Handler for handling button callbacks. Redirects to handle_user_message
    """
    update.callback_query.answer()
    handle_user_message(update, tg_context, ButtonValues(update.callback_query.data))


# helper to avoid code duplication
def _show_reminder_edit_options(
    reminder: Reminder, update: telegram.Update, command_data: dict
):
    """
    Shows the menu with options to edit a specific reminder.
    """
    # keyboard for edit
    button_list = [
        [
            telegram.InlineKeyboardButton(
                load("manage_reminders_handler__edit_text_btn"),
                callback_data=ButtonValues.MANAGE_REMINDERS__EDIT__TEXT.value,
            )
        ],
        [
            telegram.InlineKeyboardButton(
                load("manage_reminders_handler__edit_datetime_btn"),
                callback_data=ButtonValues.MANAGE_REMINDERS__EDIT__DATETIME.value,
            )
        ],
        [
            telegram.InlineKeyboardButton(
                load("manage_reminders_handler__edit_title_btn"),
                callback_data=ButtonValues.MANAGE_REMINDERS__EDIT__TITLE.value,
            )
        ],
        [
            telegram.InlineKeyboardButton(
                load("manage_reminders_handler__edit_chat_btn"),
                callback_data=ButtonValues.MANAGE_REMINDERS__EDIT__CHAT.value,
            )
        ],
        [
            (
                telegram.InlineKeyboardButton(
                    load("manage_reminders_handler__edit_suspend_btn"),
                    callback_data=ButtonValues.MANAGE_REMINDERS__EDIT__SUSPEND.value,
                )
                if reminder.is_active
                else telegram.InlineKeyboardButton(
                    load("manage_reminders_handler__edit_resume_btn"),
                    callback_data=ButtonValues.MANAGE_REMINDERS__EDIT__RESUME.value,
                )
            )
        ],
        [
            (
                telegram.InlineKeyboardButton(
                    load("manage_reminders_handler__edit_poll_active_btn"),
                    callback_data=ButtonValues.MANAGE_REMINDERS__DISABLE_POLL.value,
                )
                if reminder.send_poll
                else telegram.InlineKeyboardButton(
                    load("manage_reminders_handler__edit_poll_inactive_btn"),
                    callback_data=ButtonValues.MANAGE_REMINDERS__ENABLE_POLL.value,
                )
            )
        ],
    ]
    reply_markup = telegram.InlineKeyboardMarkup(button_list)
    weekday_str = (
        calendar.TextCalendar().formatweekday(int(reminder.weekday), 15).strip()
    )
    reply(
        load(
            "manage_reminders_handler__weekly_reminder",
            weekday=weekday_str,
            time=reminder.time,
            text=reminder.text,
        ),
        update,
        reply_markup=reply_markup,
    )
    set_next_action(
        command_data, PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION
    )


def handle_user_message(
    update: telegram.Update,
    tg_context: telegram.ext.CallbackContext,
    button: ButtonValues = None,
):
    """
    Determines the last command for the user, its current state and responds accordingly
    """
    command_id = tg_context.chat_data.get(consts.LAST_ACTIONABLE_COMMAND)
    # to understand what kind of data currently expected from user
    if not command_id:
        # No active command - forward to n8n if message exists
        if update.message and update.message.text:
            try:
                app_context = AppContext()
                user_id = get_sender_id(update)
                query = update.message.text.strip()
                app_context.n8n_client.send_webhook(user_id, query)
            except Exception as e:
                logger.error(
                    f"Failed to send message to n8n: {e}",
                    exc_info=True,
                )
        return
    command_data = tg_context.chat_data.get(command_id, {})
    tg_context.chat_data[command_id] = command_data
    next_action = command_data.get(consts.NEXT_ACTION)
    if not next_action:
        # last action for a command was successfully executed and nothing left to do
        return
    next_action = PlainTextUserAction(next_action)
    user_input = update.message.text.strip() if update.message is not None else None

    if next_action == PlainTextUserAction.GET_RUBRICS__CHOOSE_RUBRIC:
        try:
            idx = int(user_input) - 1
            rubrics = command_data.get(
                GetTasksReportData.LISTS
            ) or tg_context.chat_data.get("available_rubrics", [])
            if not (0 <= idx < len(rubrics)):
                raise ValueError
        except Exception:
            reply(
                load(
                    "invalid_rubric_number",
                    max=len(rubrics),
                ),
                update,
            )
            return

        selected = rubrics[idx]
        _generate_rubric_summary(update, selected)

        tg_context.chat_data.pop(consts.LAST_ACTIONABLE_COMMAND, None)
        tg_context.chat_data.pop(command_id, None)
        return

    # Below comes a long switch of possible next_action.
    # Following conventions are used:
    # - If you got an exception or `user_input` is invalid, call `reply('...', update)` explaining
    #   what's wrong and what user can do. We'll ask user for the same data until we get it.
    # - If data from user is good, after processing it call `set_next_action(command_data, ...)`
    #   You probably also want to call `reply` to guide user to the next piece of data.
    # - If it's the last piece of info expected from user, you should call
    #   `set_next_action(command_data, None)` so that we won't talk to user anymore,
    #   until they start a new command.
    if next_action == PlainTextUserAction.GET_TASKS_REPORT__ENTER_BOARD_URL:
        trello_client = TrelloClient()
        try:
            board = trello_client.get_board_by_url(user_input)
            trello_lists = trello_client.get_lists(board.id)
        except Exception:
            reply(load("get_tasks_report_handler__board_not_found"), update)
            return
        command_data[consts.GetTasksReportData.BOARD_ID] = board.id
        command_data[consts.GetTasksReportData.LISTS] = [
            lst.to_dict() for lst in trello_lists
        ]

        trello_lists_formatted = "\n".join(
            [f"{i + 1}) {lst.name}" for i, lst in enumerate(trello_lists)]
        )
        reply(
            load(
                "get_tasks_report_handler__choose_trello_list",
                lists=trello_lists_formatted,
            ),
            update,
        )
        set_next_action(
            command_data, PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER
        )
        return
    elif next_action == PlainTextUserAction.GET_TASKS_REPORT__ENTER_BOARD_NUMBER:
        trello_client = TrelloClient()
        focalboard_client = FocalboardClient()
        try:
            board_list = tg_context.chat_data[consts.GetTasksReportData.LISTS]
            use_focalboard = tg_context.chat_data[
                consts.GetTasksReportData.USE_FOCALBOARD
            ]
            list_idx = int(user_input) - 1
            assert 0 <= list_idx < len(board_list)
            board_id = board_list[list_idx]["id"]
            if use_focalboard:
                trello_lists = focalboard_client.get_lists(board_id, sorted=True)
                trello_lists = trello_lists[::-1]
            else:
                trello_lists = trello_client.get_lists(board_id)
                trello_lists = trello_lists[::-1]
        except Exception as e:
            logger.warning("Failed to parse board number", exc_info=e)
            reply(
                load(
                    "get_tasks_report_handler__enter_the_number",
                    max_val=len(board_list),
                ),
                update,
            )
            return

        command_data[consts.GetTasksReportData.BOARD_ID] = board_id
        command_data[consts.GetTasksReportData.USE_FOCALBOARD] = use_focalboard
        command_data[consts.GetTasksReportData.LISTS] = [
            lst.to_dict() for lst in trello_lists
        ]

        trello_lists_formatted = "\n".join(
            [
                f"{len(trello_lists) - i}) {lst.name}"
                for i, lst in enumerate(trello_lists)
            ]
        )
        reply(
            load(
                "get_tasks_report_handler__choose_trello_list",
                lists=trello_lists_formatted,
            ),
            update,
        )
        set_next_action(
            command_data, PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER
        )
        return
    elif next_action == PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER:
        try:
            trello_lists = command_data.get(consts.GetTasksReportData.LISTS, [])
            list_idx = -int(user_input)
            assert 0 > list_idx >= -len(trello_lists)
            list_id = trello_lists[list_idx]["id"]
        except Exception as e:
            logger.warning("Failed to parse list number", exc_info=e)
            reply(
                load(
                    "get_tasks_report_handler__enter_the_number",
                    max_val=len(trello_lists),
                ),
                update,
            )
            return
        command_data[consts.GetTasksReportData.LIST_ID] = list_id

        reply_markup = telegram.InlineKeyboardMarkup(
            [
                [
                    telegram.InlineKeyboardButton(
                        load("get_tasks_report_handler__no_text_btn"),
                        callback_data=ButtonValues.GET_TASKS_REPORT__NO_INTRO.value,
                    )
                ]
            ]
        )
        if not tg_context.chat_data.get("advanced"):
            add_labels = button == ButtonValues.GET_TASKS_REPORT__LABELS__NO
            command_data[consts.GetTasksReportData.INTRO_TEXT] = None
            handle_task_report(command_data, add_labels, update)
            return

        reply(
            load("get_tasks_report_handler__enter_intro"),
            update,
            reply_markup=reply_markup,
        )
        set_next_action(command_data, PlainTextUserAction.GET_TASKS_REPORT__ENTER_INTRO)
        return
    elif next_action == PlainTextUserAction.GET_TASKS_REPORT__ENTER_INTRO:
        if button is not None and button == ButtonValues.GET_TASKS_REPORT__NO_INTRO:
            command_data[consts.GetTasksReportData.INTRO_TEXT] = None
        else:
            command_data[consts.GetTasksReportData.INTRO_TEXT] = user_input

        button_list = [
            [
                telegram.InlineKeyboardButton(
                    load("common__yes"),
                    callback_data=ButtonValues.GET_TASKS_REPORT__LABELS__YES.value,
                ),
                telegram.InlineKeyboardButton(
                    load("common__no"),
                    callback_data=ButtonValues.GET_TASKS_REPORT__LABELS__NO.value,
                ),
            ]
        ]
        reply_markup = telegram.InlineKeyboardMarkup(button_list)
        reply(
            load("get_tasks_report_handler__choose_if_fill_labels"),
            update,
            reply_markup=reply_markup,
        )
        set_next_action(
            command_data, PlainTextUserAction.GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS
        )
        return
    elif next_action == PlainTextUserAction.GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS:
        if button is None:
            reply(load("user_message_handler__press_button_please"), update)
            return
        add_labels = button == ButtonValues.GET_TASKS_REPORT__LABELS__YES
        handle_task_report(command_data, add_labels, update)
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_ACTION:
        # If user sends a number, interpret it as a shortcut to edit that reminder
        if user_input and user_input.isdigit():
            reminder_ids = command_data.get(
                consts.ManageRemindersData.EXISTING_REMINDERS, []
            )
            try:
                assert 0 < int(user_input) <= len(reminder_ids)
                reminder_id, _, _ = reminder_ids[int(user_input) - 1]
            except Exception:
                reply(load("manage_reminders_handler__reminder_number_bad"), update)
                return

            command_data[consts.ManageRemindersData.ACTION_TYPE] = (
                ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT
            )
            command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID] = reminder_id
            reminder = DBClient().get_reminder_by_id(reminder_id)
            _show_reminder_edit_options(reminder, update, command_data)
            return

        if button is None:
            reply(load("user_message_handler__press_button_please"), update)
            return

        if button == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            reply(load("manager_reminders_handler__enter_chat_id"), update)
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID
            )
        elif button == ButtonValues.MANAGE_REMINDERS__ACTIONS__DELETE:
            reply(
                load("manage_reminders_handler__enter_reminder_number_to_delete"),
                update,
            )
            set_next_action(
                command_data,
                PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER,
            )
        elif button == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reply(
                load("manage_reminders_handler__enter_reminder_number_to_edit"), update
            )
            set_next_action(
                command_data,
                PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER,
            )
        command_data[consts.ManageRemindersData.ACTION_TYPE] = button
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER:
        reminder_ids = command_data[consts.ManageRemindersData.EXISTING_REMINDERS]
        try:
            assert 0 < int(user_input) <= len(reminder_ids)
            reminder_id, chat_title, reminder_name = reminder_ids[int(user_input) - 1]
        except Exception:
            reply(load("manage_reminders_handler__reminder_number_bad"), update)
            return
        command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID] = reminder_id

        action = command_data[consts.ManageRemindersData.ACTION_TYPE]
        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__DELETE:
            # keyboard for delete
            button_list = [
                [
                    telegram.InlineKeyboardButton(
                        load("common__yes"),
                        callback_data=ButtonValues.MANAGE_REMINDERS__DELETE__YES.value,
                    ),
                    telegram.InlineKeyboardButton(
                        load("common__no"),
                        callback_data=ButtonValues.MANAGE_REMINDERS__DELETE__NO.value,
                    ),
                ]
            ]
            reply_markup = telegram.InlineKeyboardMarkup(button_list)
            reply(
                load(
                    "manage_reminders_handler__confirm_delete",
                    chat=chat_title,
                    reminder=reminder_name,
                ),
                update,
                reply_markup=reply_markup,
            )
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__DELETE_REQUEST
            )
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder = DBClient().get_reminder_by_id(reminder_id)
            _show_reminder_edit_options(reminder, update, command_data)
        else:
            logger.error(f'Bad reminder action "{action}"')
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION:
        if button is None:
            reply(load("manage_reminders_handler__press_button_please"), update)
            return
        db_client = DBClient()
        reminder_id = int(command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID])
        reminder = db_client.get_reminder_by_id(reminder_id)
        if button == ButtonValues.MANAGE_REMINDERS__EDIT__TEXT:
            reply(load("manage_reminders_handler__enter_text"), update)
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT
            )
            return
        elif button == ButtonValues.MANAGE_REMINDERS__EDIT__TITLE:
            reply(
                load(
                    "manage_reminders_handler__enter_new_name", old_name=reminder.name
                ),
                update,
            )
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME
            )
            return
        elif button == ButtonValues.MANAGE_REMINDERS__EDIT__CHAT:
            reply(
                load("manage_reminders_handler__enter_chat_id", name=reminder.name),
                update,
            )
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID
            )
            return
        elif button == ButtonValues.MANAGE_REMINDERS__EDIT__DATETIME:
            reply_markup = telegram.InlineKeyboardMarkup(consts.WEEKDAY_BUTTONS)
            reply(
                load("manage_reminders_handler__choose_weekday"),
                update,
                reply_markup=reply_markup,
            )
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY
            )
            return
        elif button == ButtonValues.MANAGE_REMINDERS__EDIT__SUSPEND:
            db_client.update_reminder(reminder_id, is_active=False)
            reply(
                load(
                    "manage_reminders_handler__reminder_was_suspended",
                    name=reminder.name,
                ),
                update,
            )
            set_next_action(command_data, None)
            return
        elif button == ButtonValues.MANAGE_REMINDERS__EDIT__RESUME:
            db_client.update_reminder(reminder_id, is_active=True)
            reply(
                load(
                    "manage_reminders_handler__reminder_was_resumed",
                    next_reminder_datetime=reminder.next_reminder_datetime,
                ),
                update,
            )
            set_next_action(command_data, None)
        elif button == ButtonValues.MANAGE_REMINDERS__DISABLE_POLL:
            button_no = telegram.InlineKeyboardButton(
                load("manage_reminders_handler__disable_poll_btn"),
                callback_data=consts.ButtonValues.MANAGE_REMINDERS__DISABLE_POLL__YES.value,
            )
            keyboard = [[button_no]]
            reply(
                load("manage_reminders_handler__disable_poll_question"),
                update,
                reply_markup=telegram.InlineKeyboardMarkup(keyboard),
            )
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__DISABLE_POLL
            )
            return
        elif button == ButtonValues.MANAGE_REMINDERS__ENABLE_POLL:
            button_yes = telegram.InlineKeyboardButton(
                load("manage_reminders_handler__enable_poll_btn"),
                callback_data=consts.ButtonValues.MANAGE_REMINDERS__ENABLE_POLL__YES.value,
            )
            keyboard = [[button_yes]]
            reply(
                load("manage_reminders_handler__enable_poll_question"),
                update,
                reply_markup=telegram.InlineKeyboardMarkup(keyboard),
            )
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__ENABLE_POLL
            )
            return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENABLE_POLL:
        if button == consts.ButtonValues.MANAGE_REMINDERS__ENABLE_POLL__YES:
            db_client = DBClient()
            reminder_id = int(
                command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            reminder = db_client.get_reminder_by_id(reminder_id)
            db_client.update_reminder(reminder_id, send_poll=True)
            reply(
                load("manage_reminders_handler__poll_was_enabled"),
                update,
            )
            return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__DISABLE_POLL:
        if button == consts.ButtonValues.MANAGE_REMINDERS__DISABLE_POLL__YES:
            db_client = DBClient()
            reminder_id = int(
                command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            reminder = db_client.get_reminder_by_id(reminder_id)
            db_client.update_reminder(reminder_id, send_poll=False)
            reply(
                load("manage_reminders_handler__poll_was_disabled"),
                update,
            )
            return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__DELETE_REQUEST:
        if button is None:
            reply(load("user_message_handler__press_button_please"), update)
            return
        if button == ButtonValues.MANAGE_REMINDERS__DELETE__YES:
            DBClient().delete_reminder(
                command_data.get(consts.ManageRemindersData.CHOSEN_REMINDER_ID)
            )
            reply(load("manage_reminders_handler__reminder_was_deleted"), update)
            set_next_action(command_data, None)
        elif button == ButtonValues.MANAGE_REMINDERS__DELETE__NO:
            reply(load("manage_reminders_handler__reminder_was_not_deleted"), update)
            set_next_action(command_data, None)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID:
        try:
            chat_id = int(user_input)
            chat_title = DBClient().get_chat_name(chat_id)
        except Exception as e:
            reply(load("manage_reminders_handler__bad_chat_id"), update)
            logger.info("Failed to parse chat id", exc_info=e)
            return
        command_data[consts.ManageRemindersData.GROUP_CHAT_ID] = chat_id
        action = command_data[consts.ManageRemindersData.ACTION_TYPE]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            reply(
                load("manage_reminders_handler__enter_name", chat_title=chat_title),
                update,
            )
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME
            )
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder_id = int(
                command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            reminder = DBClient().get_reminder_by_id(reminder_id)
            DBClient().update_reminder(reminder_id, group_chat_id=chat_id)
            reply(
                load(
                    "manage_reminders_handler__reminder_set",
                    name=reminder.name,
                    chat_title=chat_title,
                ),
                update,
            )
            set_next_action(command_data, None)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME:
        command_data[consts.ManageRemindersData.REMINDER_NAME] = user_input
        action = command_data[consts.ManageRemindersData.ACTION_TYPE]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            reply(load("manage_reminders_handler__enter_text"), update)
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT
            )
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder_id = int(
                command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            DBClient().update_reminder(reminder_id, name=user_input)
            reply(load("manage_reminders_handler__reminder_name_was_changed"), update)
            set_next_action(command_data, None)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT:
        # keeps original formatting, e.g. hyperlinks
        text = update.message.text_html.strip()
        command_data[consts.ManageRemindersData.REMINDER_TEXT] = text
        action = command_data[consts.ManageRemindersData.ACTION_TYPE]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            reply_markup = telegram.InlineKeyboardMarkup(consts.WEEKDAY_BUTTONS)
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY
            )
            reply(
                load("manage_reminders_handler__choose_weekday"),
                update,
                reply_markup=reply_markup,
            )
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder_id = int(
                command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            DBClient().update_reminder(reminder_id, text=text)
            reply(load("manage_reminders_handler__reminder_text_was_changed"), update)
            set_next_action(command_data, None)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY:
        if button is None:
            reply(load("user_message_handler__press_button_please"), update)
            return
        weekday_num, weekday_name = button.value.split(":")
        command_data[consts.ManageRemindersData.WEEKDAY_NUM] = int(weekday_num)
        command_data[consts.ManageRemindersData.WEEKDAY_NAME] = weekday_name
        set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_TIME)
        reply(
            load("manage_reminders_handler__enter_time", weekday_name=weekday_name),
            update,
        )
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_TIME:
        try:
            datetime.strptime(user_input or "", "%H:%M")
        except ValueError:
            reply(load("manage_reminders_handler__time_bad"), update)
            return
        command_data[consts.ManageRemindersData.TIME] = user_input
        action = command_data[consts.ManageRemindersData.ACTION_TYPE]
        weekday_num = command_data[consts.ManageRemindersData.WEEKDAY_NUM]
        time = command_data[consts.ManageRemindersData.TIME]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder_id = int(
                command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            DBClient().update_reminder(reminder_id, weekday=weekday_num, time=time)
            set_next_action(command_data, None)
        button_yes = telegram.InlineKeyboardButton(
            load("manage_reminders_handler__poll_yes_btn"),
            callback_data=consts.ButtonValues.MANAGE_REMINDERS__POLL__YES.value,
        )
        button_no = telegram.InlineKeyboardButton(
            load("manage_reminders_handler__poll_no_btn"),
            callback_data=consts.ButtonValues.MANAGE_REMINDERS__POLL__NO.value,
        )
        buttons = [button_yes, button_no]
        reply(
            load("manage_reminders_handler__poll_question"),
            update,
            reply_markup=telegram.InlineKeyboardMarkup([buttons]),
        )
        set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__SUCCESS)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__SUCCESS:
        text = command_data.get(consts.ManageRemindersData.REMINDER_TEXT)
        group_chat_id = command_data.get(consts.ManageRemindersData.GROUP_CHAT_ID)
        name = command_data.get(consts.ManageRemindersData.REMINDER_NAME)
        weekday_num = command_data[consts.ManageRemindersData.WEEKDAY_NUM]
        weekday_name = command_data[consts.ManageRemindersData.WEEKDAY_NAME]
        time = command_data[consts.ManageRemindersData.TIME]
        if button == consts.ButtonValues.MANAGE_REMINDERS__TOGGLE_POLL__YES:
            if text is None:
                reminder_id = int(
                    command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
                )
                DBClient().update_reminder(reminder_id, weekday=weekday_num, time=time)
            else:
                DBClient().add_reminder(
                    creator_chat_id=get_sender_id(update),
                    group_chat_id=group_chat_id,
                    name=name,
                    text=text,
                    weekday_num=weekday_num,
                    time=time,
                    send_poll=True,
                )
        else:
            DBClient().add_reminder(
                creator_chat_id=get_sender_id(update),
                group_chat_id=group_chat_id,
                name=name,
                text=text,
                weekday_num=weekday_num,
                time=time,
                send_poll=False,
            )
        weekday_name = command_data[consts.ManageRemindersData.WEEKDAY_NAME]
        time = command_data[consts.ManageRemindersData.TIME]
        reply(
            load(
                "manage_reminders_handler__success_time",
                weekday_name=weekday_name,
                time=time,
            ),
            update,
        )
        set_next_action(command_data, None)
        return
    else:
        logger.error(f"Unknown user action: {next_action}")


def set_next_action(command_data: dict, next_action: PlainTextUserAction):
    command_data[consts.NEXT_ACTION] = next_action.value if next_action else next_action


def handle_new_members(
    update: telegram.Update, tg_context: telegram.ext.CallbackContext
):
    # writes chat_id and chat name to db when anybody (including the bot) is added to a new chat
    # very heuristic solution
    DBClient().set_chat_name(get_chat_id(update), get_chat_name(update))


def handle_task_report(command_data, add_labels, update):
    board_id = command_data[consts.GetTasksReportData.BOARD_ID]
    list_id = command_data[consts.GetTasksReportData.LIST_ID]
    introduction = command_data[consts.GetTasksReportData.INTRO_TEXT]
    use_focalboard = command_data[consts.GetTasksReportData.USE_FOCALBOARD]
    messages = get_tasks_report_handler.generate_report_messages(
        board_id, list_id, introduction, add_labels, use_focalboard=use_focalboard
    )
    for message in messages:
        reply(message, update)
    # finished with last action for /trello_client_get_lists
    set_next_action(command_data, None)
    return
