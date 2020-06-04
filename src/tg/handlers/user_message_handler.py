import logging

import telegram

from .utils import reply
from ...tg.handlers import get_tasks_report_handler
from ...trello.trello_client import TrelloClient
from ... import consts
from ...consts import PlainTextUserAction

logger = logging.getLogger(__name__)


def handle_callback_query(update: telegram.Update, tg_context: telegram.ext.CallbackContext):
    """
    Handler for handling button callbacks. Redirects to handle_user_message
    """
    update.callback_query.answer()
    handle_user_message(update, tg_context)


def handle_user_message(update: telegram.Update, tg_context: telegram.ext.CallbackContext):
    """
    Determines the last command for the user, its current state and responds accordingly
    """
    command_id = tg_context.chat_data.get(consts.LAST_ACTIONABLE_COMMAND)
    if not command_id:
        return
    command_data = tg_context.chat_data.get(command_id, {})
    tg_context.chat_data[command_id] = command_data
    # to understand what kind of data currently expected from user
    next_action = command_data.get(consts.NEXT_ACTION)
    if not next_action:
        # last action for a command was successfully executed and nothing left to do
        return
    next_action = PlainTextUserAction(next_action)
    user_input = update.message.text.strip() if update.message is not None else None
        
    # Below comes a long switch of possible next_action.
    # Following conventions are used:
    # - If you got an exception or `user_input` is invalid, call `reply('...', update)` explaining
    #   what's wrong and what user can do. We'll ask user for the same data until we get it.
    # - If data from user is good, after processing it call `set_next_action(command_data, ...)`
    #   You probably also want to call `reply` to guide user to the next piece of data.
    # - If it's the last piece of info expected from user, you should call
    #   `set_next_action(command_data, None)` so that we won't talk to user anymore,
    #   until they start a new command.
    if next_action == PlainTextUserAction.ENTER_BOARD_URL:
        trello_client = TrelloClient()
        try:
            board = trello_client.get_board_by_url(user_input)
            trello_lists = trello_client.get_lists(board.id)
        except Exception:
            reply(
                (
                    'Не могу найти такую доску. Пожалуйста, проверь, нет ли ошибки в ссылке на доску. '
                    'Если найдешь ошибку, пришли, пожалуйста, правильную ссылку. '
                    'Если нет – напиши Ире @irinoise или Илье @bulgak0v.'
                ),
                update
            )
            return
        command_data[consts.GetTasksReportData.BOARD_ID] = user_input
        command_data[consts.GetTasksReportData.LISTS] = [lst.to_dict() for lst in trello_lists]

        trello_lists_formatted = '\n'.join([f'{i + 1}) {lst.name}' for i, lst in enumerate(trello_lists)])
        reply(
            (
                f'Пожалуйста, пришли номер списка, задачи из которого попадут в отчет. '
                f'Вот какие списки есть в твоей доске:\n\n{trello_lists_formatted}'
            ),
            update
        )
        set_next_action(command_data, PlainTextUserAction.ENTER_LIST_NUMBER)
        return
    elif next_action == PlainTextUserAction.ENTER_LIST_NUMBER:
        try:
            trello_lists = command_data.get(consts.GetTasksReportData.LISTS, [])
            list_idx = int(user_input) - 1
            assert 0 <= list_idx < len(trello_lists)
            list_id = trello_lists[list_idx]['id']
        except Exception as e:
            logger.warning(e)
            reply('Попробуй ещё раз', update)
            return
        command_data[consts.GetTasksReportData.LIST_ID] = list_id
        reply(
            (
                'Спасибо! Хочешь добавить какой-то приветственный текст к отчету? '
                'Текст будет отображаться перед перечнем всех задач.'
            ),
            update
        )
        set_next_action(command_data, PlainTextUserAction.ENTER_INTRO)
        return
    elif next_action == PlainTextUserAction.ENTER_INTRO:
        command_data[consts.GetTasksReportData.INTRO_TEXT] = user_input
        button_list = [[
            telegram.InlineKeyboardButton("Да", callback_data="tasks_report_data__add_list__yes"),
            telegram.InlineKeyboardButton("Нет", callback_data="tasks_report_data__add_list__no"),
        ]]
        reply_markup = telegram.InlineKeyboardMarkup(button_list)
        reply('Нужно ли выводить теги (метки в Trello) в отчете?', update, reply_markup=reply_markup)
        set_next_action(command_data, PlainTextUserAction.CHOOSE_IF_FILL_LABELS)
        return
    elif next_action == PlainTextUserAction.CHOOSE_IF_FILL_LABELS:
        add_labels = update.callback_query.data == 'tasks_report_data__add_list__yes'
        # reply(f'here is add_lists with {add_labels}', update)
        # finished with last action for /trello_client_get_lists
        list_id = command_data[consts.GetTasksReportData.LIST_ID]
        messages = get_tasks_report_handler.generate_report_messages(list_id, add_labels)
        for message in messages:
            reply(message, update)
        set_next_action(command_data, None)
    else:
        logger.error(f'Unknown user action: {next_action}')


def set_next_action(command_data: dict, next_action: PlainTextUserAction):
    command_data[consts.NEXT_ACTION] = next_action.value if next_action else next_action
