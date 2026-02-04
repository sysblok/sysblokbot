import calendar
import logging
import telegram
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Optional

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
from .utils import get_sender_id, reply, get_sender_username, get_chat_id, get_chat_name

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


def handle_stateless_message(update, tg_context):
    """
    Handles messages that don't have an active command state (stateless).
    Forwards message to n8n and upserts user.
    """
    if update.message and update.message.text:
        try:
            app_context = AppContext()
            user_id = get_sender_id(update)
            username = (
                get_sender_username(update)
                if update.message.from_user.username
                else None
            )

            # Auto-create/update User record
            team_member_id = None
            if username:
                # Normalize username (remove @ if present)
                normalized_username = username.lstrip("@")
                # Find TeamMember with matching telegram username
                team_members = app_context.db_client.get_all_members()
                matching_member = next(
                    (
                        m
                        for m in team_members
                        if m.telegram
                        and m.telegram.strip().lstrip("@").lower()
                        == normalized_username.lower()
                    ),
                    None,
                )
                if matching_member:
                    team_member_id = matching_member.id

            # Upsert User record
            app_context.db_client.upsert_user_from_telegram(
                telegram_user_id=user_id,
                telegram_username=username,
                team_member_id=team_member_id,
            )

            query = update.message.text.strip()
            app_context.n8n_client.send_webhook(user_id, query)
        except Exception as e:
            logger.error(
                f"Failed to send message to n8n: {e}",
                exc_info=True,
            )


def handle_new_members(
    update: telegram.Update, tg_context: telegram.ext.CallbackContext
):
    # writes chat_id and chat name to db when anybody (including the bot) is added to a new chat
    # very heuristic solution
    DBClient().set_chat_name(get_chat_id(update), get_chat_name(update))


class BaseUserMessageHandler(ABC):
    def __init__(self, update, tg_context, command_data, user_input, button):
        self.update = update
        self.tg_context = tg_context
        self.command_data = command_data
        self.user_input = user_input
        self.button = button

    @abstractmethod
    def handle(self) -> Optional[PlainTextUserAction]:
        raise NotImplementedError


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
                update,
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
    # The caller is expected to return the next action transition to CHOOSE_EDIT_ACTION


def _handle_task_report_helper(command_data, add_labels, update):
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
    return None


class GetRubricsChooseRubricHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        try:
            idx = int(self.user_input) - 1
            rubrics = self.command_data.get(
                GetTasksReportData.LISTS
            ) or self.tg_context.chat_data.get("available_rubrics", [])
            if not (0 <= idx < len(rubrics)):
                raise ValueError
        except Exception:
            reply(
                load(
                    "invalid_rubric_number",
                    max=len(rubrics),
                ),
                self.update,
            )
            return PlainTextUserAction.GET_RUBRICS__CHOOSE_RUBRIC

        selected = rubrics[idx]
        _generate_rubric_summary(self.update, selected)

        self.tg_context.chat_data.pop(consts.LAST_ACTIONABLE_COMMAND, None)
        return None


class GetTasksReportEnterBoardUrlHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        trello_client = TrelloClient()
        try:
            board = trello_client.get_board_by_url(self.user_input)
            trello_lists = trello_client.get_lists(board.id)
        except Exception:
            reply(load("get_tasks_report_handler__board_not_found"), self.update)
            return PlainTextUserAction.GET_TASKS_REPORT__ENTER_BOARD_URL

        self.command_data[consts.GetTasksReportData.BOARD_ID] = board.id
        self.command_data[consts.GetTasksReportData.LISTS] = [
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
            self.update,
        )
        return PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER


class GetTasksReportEnterBoardNumberHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        trello_client = TrelloClient()
        focalboard_client = FocalboardClient()
        try:
            board_list = self.tg_context.chat_data[consts.GetTasksReportData.LISTS]
            use_focalboard = self.tg_context.chat_data[
                consts.GetTasksReportData.USE_FOCALBOARD
            ]
            list_idx = int(self.user_input) - 1
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
                self.update,
            )
            return PlainTextUserAction.GET_TASKS_REPORT__ENTER_BOARD_NUMBER

        self.command_data[consts.GetTasksReportData.BOARD_ID] = board_id
        self.command_data[consts.GetTasksReportData.USE_FOCALBOARD] = use_focalboard
        self.command_data[consts.GetTasksReportData.LISTS] = [
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
            self.update,
        )
        return PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER


class GetTasksReportEnterListNumberHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        try:
            trello_lists = self.command_data.get(consts.GetTasksReportData.LISTS, [])
            list_idx = -int(self.user_input)
            assert 0 > list_idx >= -len(trello_lists)
            list_id = trello_lists[list_idx]["id"]
        except Exception as e:
            logger.warning("Failed to parse list number", exc_info=e)
            reply(
                load(
                    "get_tasks_report_handler__enter_the_number",
                    max_val=len(trello_lists),
                ),
                self.update,
            )
            return PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER

        self.command_data[consts.GetTasksReportData.LIST_ID] = list_id

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
        if not self.tg_context.chat_data.get("advanced"):
            add_labels = self.button == ButtonValues.GET_TASKS_REPORT__LABELS__NO
            self.command_data[consts.GetTasksReportData.INTRO_TEXT] = None
            return _handle_task_report_helper(
                self.command_data, add_labels, self.update
            )

        reply(
            load("get_tasks_report_handler__enter_intro"),
            self.update,
            reply_markup=reply_markup,
        )
        return PlainTextUserAction.GET_TASKS_REPORT__ENTER_INTRO


class GetTasksReportEnterIntroHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        if (
            self.button is not None
            and self.button == ButtonValues.GET_TASKS_REPORT__NO_INTRO
        ):
            self.command_data[consts.GetTasksReportData.INTRO_TEXT] = None
        else:
            self.command_data[consts.GetTasksReportData.INTRO_TEXT] = self.user_input

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
            self.update,
            reply_markup=reply_markup,
        )
        return PlainTextUserAction.GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS


class GetTasksReportChooseIfFillLabelsHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        if self.button is None:
            reply(load("user_message_handler__press_button_please"), self.update)
            return PlainTextUserAction.GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS

        add_labels = self.button == ButtonValues.GET_TASKS_REPORT__LABELS__YES
        return _handle_task_report_helper(self.command_data, add_labels, self.update)


class ManageRemindersChooseActionHandler(BaseUserMessageHandler):
    def _handle_direct_reminder_edit(self):
        reminder_ids = self.command_data.get(
            consts.ManageRemindersData.EXISTING_REMINDERS, []
        )
        try:
            assert 0 < int(self.user_input) <= len(reminder_ids)
            reminder_id, _, _ = reminder_ids[int(self.user_input) - 1]
        except Exception:
            reply(load("manage_reminders_handler__reminder_number_bad"), self.update)
            return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_ACTION

        self.command_data[consts.ManageRemindersData.ACTION_TYPE] = (
            ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT
        )
        self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID] = reminder_id
        reminder = DBClient().get_reminder_by_id(reminder_id)
        _show_reminder_edit_options(reminder, self.update, self.command_data)
        return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION

    def _handle_new_action(self):
        reply(load("manager_reminders_handler__enter_chat_id"), self.update)
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID

    def _handle_delete_action(self):
        reply(
            load("manage_reminders_handler__enter_reminder_number_to_delete"),
            self.update,
        )
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER

    def _handle_edit_action(self):
        reply(
            load("manage_reminders_handler__enter_reminder_number_to_edit"), self.update
        )
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER

    def handle(self) -> Optional[PlainTextUserAction]:
        # If user sends a number, interpret it as a shortcut to edit that reminder
        if self.user_input and self.user_input.isdigit():
            return self._handle_direct_reminder_edit()

        if self.button is None:
            reply(load("user_message_handler__press_button_please"), self.update)
            return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_ACTION

        action_map = {
            ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW: self._handle_new_action,
            ButtonValues.MANAGE_REMINDERS__ACTIONS__DELETE: self._handle_delete_action,
            ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT: self._handle_edit_action,
        }

        handler_method = action_map.get(self.button)
        if handler_method:
            self.command_data[consts.ManageRemindersData.ACTION_TYPE] = self.button
            return handler_method()

        # Fallback if unknown button
        return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_ACTION


class ManageRemindersEnterReminderNumberHandler(BaseUserMessageHandler):
    def _handle_delete_action(self, chat_title, reminder_name):
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
            self.update,
            reply_markup=reply_markup,
        )
        return PlainTextUserAction.MANAGE_REMINDERS__DELETE_REQUEST

    def _handle_edit_action(self, reminder_id):
        reminder = DBClient().get_reminder_by_id(reminder_id)
        _show_reminder_edit_options(reminder, self.update, self.command_data)
        return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION

    def handle(self) -> Optional[PlainTextUserAction]:
        reminder_ids = self.command_data[consts.ManageRemindersData.EXISTING_REMINDERS]
        try:
            assert 0 < int(self.user_input) <= len(reminder_ids)
            reminder_id, chat_title, reminder_name = reminder_ids[
                int(self.user_input) - 1
            ]
        except Exception:
            reply(load("manage_reminders_handler__reminder_number_bad"), self.update)
            return PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER
        self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID] = reminder_id

        action = self.command_data[consts.ManageRemindersData.ACTION_TYPE]
        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__DELETE:
            return self._handle_delete_action(chat_title, reminder_name)
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            return self._handle_edit_action(reminder_id)
        else:
            logger.error(f'Bad reminder action "{action}"')
            return None


class ManageRemindersChooseEditActionHandler(BaseUserMessageHandler):
    def _handle_edit_text(self):
        reply(load("manage_reminders_handler__enter_text"), self.update)
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT

    def _handle_edit_title(self, reminder):
        reply(
            load("manage_reminders_handler__enter_new_name", old_name=reminder.name),
            self.update,
        )
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME

    def _handle_edit_chat(self, reminder):
        reply(
            load("manage_reminders_handler__enter_chat_id", name=reminder.name),
            self.update,
        )
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID

    def _handle_edit_datetime(self):
        reply_markup = telegram.InlineKeyboardMarkup(consts.WEEKDAY_BUTTONS)
        reply(
            load("manage_reminders_handler__choose_weekday"),
            self.update,
            reply_markup=reply_markup,
        )
        return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY

    def _handle_suspend(self, reminder_id, reminder):
        DBClient().update_reminder(reminder_id, is_active=False)
        reply(
            load(
                "manage_reminders_handler__reminder_was_suspended",
                name=reminder.name,
            ),
            self.update,
        )
        return None

    def _handle_resume(self, reminder_id, reminder):
        DBClient().update_reminder(reminder_id, is_active=True)
        reply(
            load(
                "manage_reminders_handler__reminder_was_resumed",
                next_reminder_datetime=reminder.next_reminder_datetime,
            ),
            self.update,
        )
        return None

    def _handle_disable_poll_request(self):
        button_no = telegram.InlineKeyboardButton(
            load("manage_reminders_handler__disable_poll_btn"),
            callback_data=consts.ButtonValues.MANAGE_REMINDERS__DISABLE_POLL__YES.value,
        )
        keyboard = [[button_no]]
        reply(
            load("manage_reminders_handler__disable_poll_question"),
            self.update,
            reply_markup=telegram.InlineKeyboardMarkup(keyboard),
        )
        return PlainTextUserAction.MANAGE_REMINDERS__DISABLE_POLL

    def _handle_enable_poll_request(self):
        button_yes = telegram.InlineKeyboardButton(
            load("manage_reminders_handler__enable_poll_btn"),
            callback_data=consts.ButtonValues.MANAGE_REMINDERS__ENABLE_POLL__YES.value,
        )
        keyboard = [[button_yes]]
        reply(
            load("manage_reminders_handler__enable_poll_question"),
            self.update,
            reply_markup=telegram.InlineKeyboardMarkup(keyboard),
        )
        return PlainTextUserAction.MANAGE_REMINDERS__ENABLE_POLL

    def handle(self) -> Optional[PlainTextUserAction]:
        if self.button is None:
            reply(load("manage_reminders_handler__press_button_please"), self.update)
            return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION

        reminder_id = int(
            self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
        )
        reminder = DBClient().get_reminder_by_id(reminder_id)

        action_map = {
            ButtonValues.MANAGE_REMINDERS__EDIT__TEXT: self._handle_edit_text,
            ButtonValues.MANAGE_REMINDERS__EDIT__TITLE: lambda: self._handle_edit_title(
                reminder
            ),
            ButtonValues.MANAGE_REMINDERS__EDIT__CHAT: lambda: self._handle_edit_chat(
                reminder
            ),
            ButtonValues.MANAGE_REMINDERS__EDIT__DATETIME: self._handle_edit_datetime,
            ButtonValues.MANAGE_REMINDERS__EDIT__SUSPEND: lambda: self._handle_suspend(
                reminder_id, reminder
            ),
            ButtonValues.MANAGE_REMINDERS__EDIT__RESUME: lambda: self._handle_resume(
                reminder_id, reminder
            ),
            ButtonValues.MANAGE_REMINDERS__DISABLE_POLL: self._handle_disable_poll_request,
            ButtonValues.MANAGE_REMINDERS__ENABLE_POLL: self._handle_enable_poll_request,
        }

        handler = action_map.get(self.button)
        if handler:
            return handler()

        return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION


class ManageRemindersEnablePollHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        if self.button == consts.ButtonValues.MANAGE_REMINDERS__ENABLE_POLL__YES:
            db_client = DBClient()
            reminder_id = int(
                self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            db_client.update_reminder(reminder_id, send_poll=True)
            reply(
                load("manage_reminders_handler__poll_was_enabled"),
                self.update,
            )
            return None
        return PlainTextUserAction.MANAGE_REMINDERS__ENABLE_POLL


class ManageRemindersDisablePollHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        if self.button == consts.ButtonValues.MANAGE_REMINDERS__DISABLE_POLL__YES:
            db_client = DBClient()
            reminder_id = int(
                self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            db_client.update_reminder(reminder_id, send_poll=False)
            reply(
                load("manage_reminders_handler__poll_was_disabled"),
                self.update,
            )
            return None
        return PlainTextUserAction.MANAGE_REMINDERS__DISABLE_POLL


class ManageRemindersDeleteRequestHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        if self.button is None:
            reply(load("user_message_handler__press_button_please"), self.update)
            return PlainTextUserAction.MANAGE_REMINDERS__DELETE_REQUEST

        if self.button == ButtonValues.MANAGE_REMINDERS__DELETE__YES:
            DBClient().delete_reminder(
                self.command_data.get(consts.ManageRemindersData.CHOSEN_REMINDER_ID)
            )
            reply(load("manage_reminders_handler__reminder_was_deleted"), self.update)
            return None
        elif self.button == ButtonValues.MANAGE_REMINDERS__DELETE__NO:
            reply(
                load("manage_reminders_handler__reminder_was_not_deleted"), self.update
            )
            return None
        return PlainTextUserAction.MANAGE_REMINDERS__DELETE_REQUEST


class ManageRemindersEnterChatIdHandler(BaseUserMessageHandler):
    def _handle_new_action(self, chat_title):
        reply(
            load("manage_reminders_handler__enter_name", chat_title=chat_title),
            self.update,
        )
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME

    def _handle_edit_action(self, chat_title, chat_id):
        reminder_id = int(
            self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
        )
        reminder = DBClient().get_reminder_by_id(reminder_id)
        DBClient().update_reminder(reminder_id, group_chat_id=chat_id)
        reply(
            load(
                "manage_reminders_handler__reminder_set",
                name=reminder.name,
                chat_title=chat_title,
            ),
            self.update,
        )
        return None

    def handle(self) -> Optional[PlainTextUserAction]:
        try:
            chat_id = int(self.user_input)
            chat_title = DBClient().get_chat_name(chat_id)
        except Exception as e:
            reply(load("manage_reminders_handler__bad_chat_id"), self.update)
            logger.info("Failed to parse chat id", exc_info=e)
            return PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID

        self.command_data[consts.ManageRemindersData.GROUP_CHAT_ID] = chat_id
        action = self.command_data[consts.ManageRemindersData.ACTION_TYPE]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            return self._handle_new_action(chat_title)
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            return self._handle_edit_action(chat_title, chat_id)
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID


class ManageRemindersEnterNameHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        self.command_data[consts.ManageRemindersData.REMINDER_NAME] = self.user_input
        action = self.command_data[consts.ManageRemindersData.ACTION_TYPE]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            reply(load("manage_reminders_handler__enter_text"), self.update)
            return PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder_id = int(
                self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            DBClient().update_reminder(reminder_id, name=self.user_input)
            reply(
                load("manage_reminders_handler__reminder_name_was_changed"), self.update
            )
            return None
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME


class ManageRemindersEnterTextHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        # keeps original formatting, e.g. hyperlinks
        text = self.update.message.text_html.strip()
        self.command_data[consts.ManageRemindersData.REMINDER_TEXT] = text
        action = self.command_data[consts.ManageRemindersData.ACTION_TYPE]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            reply_markup = telegram.InlineKeyboardMarkup(consts.WEEKDAY_BUTTONS)
            reply(
                load("manage_reminders_handler__choose_weekday"),
                self.update,
                reply_markup=reply_markup,
            )
            return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder_id = int(
                self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            DBClient().update_reminder(reminder_id, text=text)
            reply(
                load("manage_reminders_handler__reminder_text_was_changed"), self.update
            )
            return None
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT


class ManageRemindersChooseWeekdayHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        if self.button is None:
            reply(load("user_message_handler__press_button_please"), self.update)
            return PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY

        weekday_num, weekday_name = self.button.value.split(":")
        self.command_data[consts.ManageRemindersData.WEEKDAY_NUM] = int(weekday_num)
        self.command_data[consts.ManageRemindersData.WEEKDAY_NAME] = weekday_name
        reply(
            load("manage_reminders_handler__enter_time", weekday_name=weekday_name),
            self.update,
        )
        return PlainTextUserAction.MANAGE_REMINDERS__ENTER_TIME


class ManageRemindersEnterTimeHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        try:
            datetime.strptime(self.user_input or "", "%H:%M")
        except ValueError:
            reply(load("manage_reminders_handler__time_bad"), self.update)
            return PlainTextUserAction.MANAGE_REMINDERS__ENTER_TIME
        self.command_data[consts.ManageRemindersData.TIME] = self.user_input
        action = self.command_data[consts.ManageRemindersData.ACTION_TYPE]
        weekday_num = self.command_data[consts.ManageRemindersData.WEEKDAY_NUM]
        time = self.command_data[consts.ManageRemindersData.TIME]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder_id = int(
                self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
            )
            DBClient().update_reminder(reminder_id, weekday=weekday_num, time=time)
            return None

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
            self.update,
            reply_markup=telegram.InlineKeyboardMarkup([buttons]),
        )
        return PlainTextUserAction.MANAGE_REMINDERS__SUCCESS


class ManageRemindersSuccessHandler(BaseUserMessageHandler):
    def handle(self) -> Optional[PlainTextUserAction]:
        text = self.command_data.get(consts.ManageRemindersData.REMINDER_TEXT)
        group_chat_id = self.command_data.get(consts.ManageRemindersData.GROUP_CHAT_ID)
        name = self.command_data.get(consts.ManageRemindersData.REMINDER_NAME)
        weekday_num = self.command_data[consts.ManageRemindersData.WEEKDAY_NUM]
        weekday_name = self.command_data[consts.ManageRemindersData.WEEKDAY_NAME]
        time = self.command_data[consts.ManageRemindersData.TIME]

        if self.button == consts.ButtonValues.MANAGE_REMINDERS__TOGGLE_POLL__YES:
            if text is None:
                reminder_id = int(
                    self.command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID]
                )
                DBClient().update_reminder(reminder_id, weekday=weekday_num, time=time)
            else:
                DBClient().add_reminder(
                    creator_chat_id=get_sender_id(self.update),
                    group_chat_id=group_chat_id,
                    name=name,
                    text=text,
                    weekday_num=weekday_num,
                    time=time,
                    send_poll=True,
                )
        else:
            DBClient().add_reminder(
                creator_chat_id=get_sender_id(self.update),
                group_chat_id=group_chat_id,
                name=name,
                text=text,
                weekday_num=weekday_num,
                time=time,
                send_poll=False,
            )
        weekday_name = self.command_data[consts.ManageRemindersData.WEEKDAY_NAME]
        time = self.command_data[consts.ManageRemindersData.TIME]
        reply(
            load(
                "manage_reminders_handler__success_time",
                weekday_name=weekday_name,
                time=time,
            ),
            self.update,
        )
        return None
