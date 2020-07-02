import calendar
from datetime import datetime
import logging

import telegram

from .utils import get_chat_id, get_chat_name, get_sender_id, reply
from ...db.db_client import DBClient
from ...tg.handlers import get_tasks_report_handler
from ...trello.trello_client import TrelloClient
from ... import consts
from ...consts import PlainTextUserAction, ButtonValues

logger = logging.getLogger(__name__)


def handle_callback_query(update: telegram.Update, tg_context: telegram.ext.CallbackContext):
    """
    Handler for handling button callbacks. Redirects to handle_user_message
    """
    update.callback_query.answer()
    handle_user_message(update, tg_context, ButtonValues(update.callback_query.data))


def handle_user_message(
        update: telegram.Update,
        tg_context: telegram.ext.CallbackContext,
        button: ButtonValues = None
):
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
    if next_action == PlainTextUserAction.GET_TASKS_REPORT__ENTER_BOARD_URL:
        trello_client = TrelloClient()
        try:
            board = trello_client.get_board_by_url(user_input)
            trello_lists = trello_client.get_lists(board.id)
        except Exception:
            reply(
                (
                    'Не могу найти такую доску. Пожалуйста, проверь, нет ли ошибки в '
                    'ссылке на доску. Если найдешь ошибку, пришли, пожалуйста, '
                    'правильную ссылку. Если нет – напиши Ире @irinoise или Илье @bulgak0v.'
                ),
                update
            )
            return
        command_data[consts.GetTasksReportData.BOARD_ID] = board.id
        command_data[consts.GetTasksReportData.LISTS] = [lst.to_dict() for lst in trello_lists]

        trello_lists_formatted = '\n'.join(
            [f'{i + 1}) {lst.name}' for i, lst in enumerate(trello_lists)]
        )
        reply(
            (
                f'Пожалуйста, пришли номер списка, задачи из которого попадут в отчет. '
                f'Вот какие списки есть в твоей доске:\n\n{trello_lists_formatted}'
            ),
            update
        )
        set_next_action(command_data, PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER)
        return
    elif next_action == PlainTextUserAction.GET_TASKS_REPORT__ENTER_LIST_NUMBER:
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

        reply_markup = telegram.InlineKeyboardMarkup(
            [[telegram.InlineKeyboardButton(
                "Без текста",
                callback_data=ButtonValues.GET_TASKS_REPORT__NO_INTRO.value
            )]]
        )
        reply(
            (
                'Спасибо! Хочешь добавить какой-то приветственный текст к отчету? '
                'Текст будет отображаться перед перечнем всех задач.'
            ),
            update,
            reply_markup=reply_markup
        )
        set_next_action(command_data, PlainTextUserAction.GET_TASKS_REPORT__ENTER_INTRO)
        return
    elif next_action == PlainTextUserAction.GET_TASKS_REPORT__ENTER_INTRO:
        if button is not None and button == ButtonValues.GET_TASKS_REPORT__NO_INTRO:
            command_data[consts.GetTasksReportData.INTRO_TEXT] = None
        else:
            command_data[consts.GetTasksReportData.INTRO_TEXT] = user_input

        button_list = [[
            telegram.InlineKeyboardButton(
                "Да",
                callback_data=ButtonValues.GET_TASKS_REPORT__LABELS__YES.value
            ),
            telegram.InlineKeyboardButton(
                "Нет",
                callback_data=ButtonValues.GET_TASKS_REPORT__LABELS__NO.value
            ),
        ]]
        reply_markup = telegram.InlineKeyboardMarkup(button_list)
        reply(
            'Нужно ли выводить теги (метки в Trello) в отчете?',
            update, reply_markup=reply_markup
        )
        set_next_action(command_data, PlainTextUserAction.GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS)
        return
    elif next_action == PlainTextUserAction.GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS:
        if button is None:
            reply('Нажми кнопку :)', update)
            return
        add_labels = (button == ButtonValues.GET_TASKS_REPORT__LABELS__YES)
        board_id = command_data[consts.GetTasksReportData.BOARD_ID]
        list_id = command_data[consts.GetTasksReportData.LIST_ID]
        introduction = command_data[consts.GetTasksReportData.INTRO_TEXT]
        messages = get_tasks_report_handler.generate_report_messages(
            board_id,
            list_id,
            introduction,
            add_labels
        )
        for message in messages:
            reply(message, update)
        # finished with last action for /trello_client_get_lists
        set_next_action(command_data, None)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_ACTION:
        if button is None:
            reply('Нажми кнопку :)', update)
            return
        if button == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            reply((
                'Пришли, пожалуйста, id чата, куда должно отправляться напоминание. '
                'Для получения id тебе нужно добавить меня в этот чат и вызвать там '
                'команду /get_chat_id.'
            ), update)
            set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID)
        elif button == ButtonValues.MANAGE_REMINDERS__ACTIONS__DELETE:
            reply('Пожалуйста, пришли номер напоминания, которое ты хочешь удалить.', update)
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER
            )
        elif button == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reply('Пожалуйста, пришли номер напоминания, которое ты хочешь изменить.', update)
            set_next_action(
                command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER
            )
        command_data[consts.ManageRemindersData.ACTION_TYPE] = button
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_REMINDER_NUMBER:
        reminder_ids = command_data[consts.ManageRemindersData.EXISTING_REMINDERS]
        try:
            assert 0 < int(user_input) <= len(reminder_ids)
            reminder_id, chat_title, reminder_name = reminder_ids[int(user_input) - 1]
        except Exception:
            reply('Кажется, в номере ошибка. Пожалуйста, введи правильный номер.', update)
            return
        command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID] = reminder_id

        action = command_data[consts.ManageRemindersData.ACTION_TYPE]
        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__DELETE:
            # keyboard for delete
            button_list = [[
                telegram.InlineKeyboardButton(
                    "Да",
                    callback_data=ButtonValues.MANAGE_REMINDERS__DELETE__YES.value
                ),
                telegram.InlineKeyboardButton(
                    "Нет",
                    callback_data=ButtonValues.MANAGE_REMINDERS__DELETE__NO.value
                ),
            ]]
            reply_markup = telegram.InlineKeyboardMarkup(button_list)
            reply(
                f'Пожалуйста, подтверди, что ты хочешь удалить напоминание '
                f'<b>{chat_title}: {reminder_name}</b>.',
                update,
                reply_markup=reply_markup
            )
            set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__DELETE_REQUEST)
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder = DBClient().get_reminder_by_id(reminder_id)
            # keyboard for edit
            button_list = [[
                telegram.InlineKeyboardButton(
                    "Изменить текст",
                    callback_data=ButtonValues.MANAGE_REMINDERS__EDIT__TEXT.value
                ),
                telegram.InlineKeyboardButton(
                    "Изменить время",
                    callback_data=ButtonValues.MANAGE_REMINDERS__EDIT__DATETIME.value
                ),
                telegram.InlineKeyboardButton(
                    "Приостановить" if reminder.is_active else "Возобновить",
                    callback_data=ButtonValues.MANAGE_REMINDERS__EDIT__SUSPEND.value
                ),
            ]]
            reply_markup = telegram.InlineKeyboardMarkup(button_list)
            weekday_str = calendar.TextCalendar().formatweekday(int(reminder.weekday), 15).strip()
            reply(
                f'<b>{weekday_str} {reminder.time} (раз в неделю)</b>\n\n"{reminder.text}"',
                update,
                reply_markup=reply_markup
            )
            set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION)
        else:
            logger.error(f'Bad reminder action "{action}"')
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_EDIT_ACTION:
        if button is None:
            reply('Нажми кнопку :)', update)
            return
        if button == ButtonValues.MANAGE_REMINDERS__EDIT__TEXT:
            reply('Пожалуйста, введи текст напоминания.', update)
            set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT)
            return
        elif button == ButtonValues.MANAGE_REMINDERS__EDIT__DATETIME:
            reply_markup = telegram.InlineKeyboardMarkup(consts.WEEKDAY_BUTTONS)
            reply(
                'Пожалуйста, выбери день для отправки напоминания в чат.',
                update,
                reply_markup=reply_markup
            )
            set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY)
            return
        elif button == ButtonValues.MANAGE_REMINDERS__EDIT__SUSPEND:
            db_client = DBClient()
            reminder_id = int(command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID])
            reminder = db_client.get_reminder_by_id(reminder_id)
            if reminder.is_active:
                db_client.update_reminder(reminder_id, is_active=False)
                reply(f'Напоминание <code>{reminder.name}</code> было приостановлено', update)
            else:
                db_client.update_reminder(reminder_id, is_active=True)
                reply(
                    f'Напоминание было возобновлено. Следующее напоминание в '
                    f'<code>{reminder.next_reminder_datetime}</code>.',
                    update
                )
            set_next_action(command_data, None)
            return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__DELETE_REQUEST:
        if button is None:
            reply('Нажми кнопку :)', update)
            return
        if button == ButtonValues.MANAGE_REMINDERS__DELETE__YES:
            DBClient().delete_reminder(
                command_data.get(consts.ManageRemindersData.CHOSEN_REMINDER_ID)
            )
            reply('Напоминание удалено.', update)
            set_next_action(command_data, None)
        elif button == ButtonValues.MANAGE_REMINDERS__DELETE__NO:
            reply('Напоминание не было удалено.', update)
            set_next_action(command_data, None)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_CHAT_ID:
        try:
            chat_id = int(user_input)
            chat_title = DBClient().get_chat_name(chat_id)
        except Exception:
            reply((
                'Пожалуйста, проверь, нет ли ошибки в id. Если найдешь ошибку, пришли, '
                'пожалуйста, правильный id. Если нет – напиши Ире @irinoise или Илье @bulgak0v.'
            ), update)
            return
        command_data[consts.ManageRemindersData.GROUP_CHAT_ID] = chat_id
        reply((
            f'Пожалуйста, введи название напоминания, которое ты хочешь отправлять в чат '
            f'"{chat_title}". Название будет отображаться в списке твоих активных напоминаний.'
        ), update)
        set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_NAME:
        command_data[consts.ManageRemindersData.REMINDER_NAME] = user_input
        reply('Пожалуйста, введи текст напоминания.', update)
        set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_TEXT:
        command_data[consts.ManageRemindersData.REMINDER_TEXT] = user_input
        action = command_data[consts.ManageRemindersData.ACTION_TYPE]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            reply_markup = telegram.InlineKeyboardMarkup(consts.WEEKDAY_BUTTONS)
            set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY)
            reply(
                'Пожалуйста, выбери день для отправки напоминания в чат.',
                update,
                reply_markup=reply_markup
            )
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder_id = int(command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID])
            DBClient().update_reminder(reminder_id, text=user_input)
            reply('Спасибо, текст напоминания сохранен.', update)
            set_next_action(command_data, None)
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__CHOOSE_WEEKDAY:
        if button is None:
            reply('Нажми кнопку :)', update)
            return
        weekday_num, weekday_name = button.value.split(':')
        command_data[consts.ManageRemindersData.WEEKDAY_NUM] = int(weekday_num)
        command_data[consts.ManageRemindersData.WEEKDAY_NAME] = weekday_name
        set_next_action(command_data, PlainTextUserAction.MANAGE_REMINDERS__ENTER_TIME)
        reply(
            (
                f'Буду присылать напоминание в <code>{weekday_name}</code>.\n\n'
                f'В какое время отправлять напоминание? Пожалуйста, укажи московское время '
                f'в формате hh:mm (например, 15:00)'
            ),
            update
        )
        return
    elif next_action == PlainTextUserAction.MANAGE_REMINDERS__ENTER_TIME:
        try:
            datetime.strptime(user_input or '', '%H:%M')
        except ValueError:
            reply(
                (
                    'Не могу установить напоминание на это время. Пожалуйста, проверь, нет ли '
                    'ошибки в формате hh:mm (например, 15:00). Если найдешь ошибку, пришли, '
                    'пожалуйста, правильное время. '
                    'Если нет – напиши Ире @irinoise или Илье @bulgak0v.'
                ),
                update
            )
            return
        command_data[consts.ManageRemindersData.TIME] = user_input

        weekday_num = command_data[consts.ManageRemindersData.WEEKDAY_NUM]
        weekday_name = command_data[consts.ManageRemindersData.WEEKDAY_NAME]
        time = command_data[consts.ManageRemindersData.TIME]
        action = command_data[consts.ManageRemindersData.ACTION_TYPE]

        if action == ButtonValues.MANAGE_REMINDERS__ACTIONS__NEW:
            name = command_data[consts.ManageRemindersData.REMINDER_NAME]
            text = command_data[consts.ManageRemindersData.REMINDER_TEXT]
            group_chat_id = command_data[consts.ManageRemindersData.GROUP_CHAT_ID]
            DBClient().add_reminder(
                creator_chat_id=get_sender_id(update),
                group_chat_id=group_chat_id,
                name=name,
                text=text,
                weekday_num=weekday_num,
                time=time
            )
        elif action == ButtonValues.MANAGE_REMINDERS__ACTIONS__EDIT:
            reminder_id = int(command_data[consts.ManageRemindersData.CHOSEN_REMINDER_ID])
            DBClient().update_reminder(reminder_id, weekday=weekday_num, time=time)
        set_next_action(command_data, None)
        reply(
            (
                f'Принято! Напоминание будет отправляться раз в неделю '
                f'в <code>{weekday_name} {time}</code>.'
            ),
            update
        )
    else:
        logger.error(f'Unknown user action: {next_action}')


def set_next_action(command_data: dict, next_action: PlainTextUserAction):
    command_data[consts.NEXT_ACTION] = next_action.value if next_action else next_action


def handle_new_members(
    update: telegram.Update,
    tg_context: telegram.ext.CallbackContext
):
    # writes chat_id and chat name to db when anybody (including the bot) is added to a new chat
    # very heuristic solution
    DBClient().set_chat_name(get_chat_id(update), get_chat_name(update))
