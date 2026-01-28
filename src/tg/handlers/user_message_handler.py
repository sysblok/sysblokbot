import logging
import telegram
from ... import consts
from ...consts import (
    ButtonValues,
    PlainTextUserAction,
)


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
    PlainTextUserAction.GET_RUBRICS__CHOOSE_RUBRIC: flow_handlers.GetRubricsChooseRubricHandler,
    PlainTextUserAction.GET_TASKS_REPORT__ENTER_BOARD_URL: flow_handlers.GetTasksReportEnterBoardUrlHandler,
    PlainTextUserAction.GET_TASKS_REPORT__ENTER_BOARD_NUMBER: flow_handlers.GetTasksReportEnterBoardNumberHandler,
    PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER: flow_handlers.GetTasksReportEnterListNumberHandler,
    PlainTextUserAction.GET_TASKS_REPORT__ENTER_INTRO: flow_handlers.GetTasksReportEnterIntroHandler,
    PlainTextUserAction.GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS: flow_handlers.GetTasksReportChooseIfFillLabelsHandler,
    PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_ACTION: flow_handlers.ManageRemindersChooseActionHandler,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER: flow_handlers.ManageRemindersEnterReminderNumberHandler,
    PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION: flow_handlers.ManageRemindersChooseEditActionHandler,
    PlainTextUserAction.MANAGE_REMINDERS__ENABLE_POLL: flow_handlers.ManageRemindersEnablePollHandler,
    PlainTextUserAction.MANAGE_REMINDERS__DISABLE_POLL: flow_handlers.ManageRemindersDisablePollHandler,
    PlainTextUserAction.MANAGE_REMINDERS__DELETE_REQUEST: flow_handlers.ManageRemindersDeleteRequestHandler,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID: flow_handlers.ManageRemindersEnterChatIdHandler,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME: flow_handlers.ManageRemindersEnterNameHandler,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT: flow_handlers.ManageRemindersEnterTextHandler,
    PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY: flow_handlers.ManageRemindersChooseWeekdayHandler,
    PlainTextUserAction.MANAGE_REMINDERS__ENTER_TIME: flow_handlers.ManageRemindersEnterTimeHandler,
    PlainTextUserAction.MANAGE_REMINDERS__SUCCESS: flow_handlers.ManageRemindersSuccessHandler,
}


def set_next_action(command_data: dict, next_action: PlainTextUserAction):
    command_data[consts.NEXT_ACTION] = next_action.value if next_action else next_action


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
        flow_handlers.handle_stateless_message(update, tg_context)
        return
    command_data = tg_context.chat_data.get(command_id, {})
    tg_context.chat_data[command_id] = command_data
    next_action = command_data.get(consts.NEXT_ACTION)
    if not next_action:
        # last action for a command was successfully executed and nothing left to do
        return
    next_action_enum = PlainTextUserAction(next_action)
    user_input = update.message.text.strip() if update.message is not None else None

    if next_action_enum in ACTION_HANDLERS:
        handler_cls = ACTION_HANDLERS[next_action_enum]
        handler = handler_cls(update, tg_context, command_data, user_input, button)
        next_state = handler.handle()
        set_next_action(command_data, next_state)
        return

    logger.error(f"Unknown user action: {next_action}")
