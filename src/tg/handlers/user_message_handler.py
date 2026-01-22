import logging
import telegram
from ... import consts
from ...app_context import AppContext
from ...consts import (
    ButtonValues,
    PlainTextUserAction,
)
from ...db.db_client import DBClient
from .utils import get_chat_id, get_chat_name, get_sender_id, get_sender_username
from . import flow_handlers

logger = logging.getLogger(__name__)


def handle_callback_query(
    update: telegram.Update, tg_context: telegram.ext.CallbackContext
):
    """
    Handler for handling button callbacks. Redirects to handle_user_message
    """
    update.callback_query.answer()
    handle_user_message(update, tg_context, ButtonValues(update.callback_query.data))


ACTION_HANDLERS = {
    PlainTextUserAction.GET_RUBRICS__CHOOSE_RUBRIC: flow_handlers.handle_get_rubrics_choose_rubric,
    PlainTextUserAction.GET_TASKS_REPORT__ENTER_BOARD_URL: flow_handlers.handle_get_tasks_report_enter_board_url,
    PlainTextUserAction.GET_TASKS_REPORT__ENTER_BOARD_NUMBER: flow_handlers.handle_get_tasks_report_enter_board_number,
    PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER: flow_handlers.handle_get_tasks_report_enter_list_number,
    PlainTextUserAction.GET_TASKS_REPORT__ENTER_INTRO: flow_handlers.handle_get_tasks_report_enter_intro,
    PlainTextUserAction.GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS: flow_handlers.handle_get_tasks_report_choose_if_fill_labels,
    PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_ACTION: flow_handlers.handle_manage_reminders_choose_action,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER: flow_handlers.handle_manage_reminders_enter_reminder_number,
    PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION: flow_handlers.handle_manage_reminders_choose_edit_action,
    PlainTextUserAction.MANAGE_REMINDERS__ENABLE_POLL: flow_handlers.handle_manage_reminders_enable_poll,
    PlainTextUserAction.MANAGE_REMINDERS__DISABLE_POLL: flow_handlers.handle_manage_reminders_disable_poll,
    PlainTextUserAction.MANAGE_REMINDERS__DELETE_REQUEST: flow_handlers.handle_manage_reminders_delete_request,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID: flow_handlers.handle_manage_reminders_enter_chat_id,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME: flow_handlers.handle_manage_reminders_enter_name,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT: flow_handlers.handle_manage_reminders_enter_text,
    PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY: flow_handlers.handle_manage_reminders_choose_weekday,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_TIME: flow_handlers.handle_manage_reminders_enter_time,
    PlainTextUserAction.MANAGE_REMINDERS__SUCCESS: flow_handlers.handle_manage_reminders_success,
}


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
        return
    command_data = tg_context.chat_data.get(command_id, {})
    tg_context.chat_data[command_id] = command_data
    next_action = command_data.get(consts.NEXT_ACTION)
    if not next_action:
        # last action for a command was successfully executed and nothing left to do
        return
    next_action = PlainTextUserAction(next_action)
    user_input = update.message.text.strip() if update.message is not None else None

    if next_action in ACTION_HANDLERS:
        ACTION_HANDLERS[next_action](
            update, tg_context, command_data, user_input, button
        )
        return

    logger.error(f"Unknown user action: {next_action}")


def handle_new_members(
    update: telegram.Update, tg_context: telegram.ext.CallbackContext
):
    # writes chat_id and chat name to db when anybody (including the bot) is added to a new chat
    # very heuristic solution
    DBClient().set_chat_name(get_chat_id(update), get_chat_name(update))
