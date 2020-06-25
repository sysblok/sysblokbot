"""App-level constants"""
import os
from datetime import timedelta, timezone
from enum import Enum

LOG_FORMAT = '%(asctime)s - %(name)s\t- %(levelname)s\t- %(message)s'

COMMIT_URL = f'https://github.com/sysblok/sysblokbot/commit/{os.environ.get("COMMIT_HASH")}'
COMMIT_HASH = os.environ.get('COMMIT_HASH_SHORT')


class AppSource(Enum):
    DEFAULT = 'manual'
    GITHUB = 'github CI'


APP_SOURCE = os.environ.get('APP_SOURCE', AppSource.DEFAULT.value)

ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, 'config.json')
CONFIG_OVERRIDE_PATH = os.path.join(ROOT_DIR, 'config_override.json')

CONFIG_RELOAD_MINUTES = 15
MSK_TIMEZONE = timezone(timedelta(hours=3))

# Upper level config keys
TELEGRAM_CONFIG = 'telegram'
TRELLO_CONFIG = 'trello'
SHEETS_CONFIG = 'sheets'
DRIVE_CONFIG = 'drive'
JOBS_CONFIG = 'jobs'
DB_CONFIG = 'db'

# Jobs-related keys
EVERY = 'every'
AT = 'at'
SEND_TO = 'send_to'

# Telegram keys
TELEGRAM_MANAGER_IDS = 'manager_chat_ids'

# Trello keys
TRELLO_BOARD_ID = 'board_id'


class TrelloCardColor(Enum):
    GREEN = 'green'
    YELLOW = 'yellow'
    RED = 'red'
    ORANGE = 'orange'
    PURPLE = 'purple'
    BLUE = 'blue'
    SKY = 'sky'
    LIME = 'lime'
    PINK = 'pink'
    BLACK = 'black'


class TrelloListAlias(Enum):
    TOPIC_SUGGESTION = 'Идея для статьи'
    TOPIC_READY = 'Готовая тема'
    IN_PROGRESS = 'Уже пишу'
    TO_EDITOR = 'Редактору'
    EDITED_NEXT_WEEK = 'На редактуре на след.неделю'
    EDITED_SOMETIMES = 'Отредактировано впрок'
    TO_CHIEF_EDITOR = 'Финальная проверка и отбор'
    PROOFREADING = 'Отобрано для публикации на неделю'
    DONE = 'Готово для верстки'
    BACK_BURNER = 'Долгий Ящик'


class TrelloCustomFieldTypeAlias(Enum):
    AUTHOR = 'Автор'
    GOOGLE_DOC = 'Google Doc'
    EDITOR = 'Редактор'
    TITLE = 'Название поста'
    ILLUSTRATOR = 'Иллюстратор'
    COVER = 'Обложка'
    WEBSITE = 'Сайт'
    VKONTAKTE = 'ВКонтакте'
    TELEGRAM = 'Telegram'


class TrelloCustomFieldTypes(Enum):
    TEXT = 'text'
    CHECKBOX = 'checkbox'
    LIST = 'list'


# constants for interactive commands (data stored in update.chat_data)
LAST_ACTIONABLE_COMMAND = 'last_actionable_command'
NEXT_ACTION = 'next_action'


class PlainTextUserAction(Enum):
    """
    When adding an item here, go to user_message_handler.py to process it
    """
    # /get_tasks_report items
    GET_TASKS_REPORT__ENTER_BOARD_URL = 'get_tasks_report__board_url'
    GET_TASKS_REPORT__ENTER_LIST_NUMBER = 'get_tasks_report__list_number'
    GET_TASKS_REPORT__ENTER_INTRO = 'get_tasks_report__introduction'
    GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS = 'get_tasks_report__fill_labels'
    # /manage_reminders items
    MANAGE_REMINDERS__CHOOSE_ACTION = 'manage_reminders__action'
    MANAGE_REMINDERS__ENTER_CHAT_ID = 'manage_reminders__chat_id'
    MANAGE_REMINDERS__ENTER_NAME = 'manage_reminders__name'
    MANAGE_REMINDERS__ENTER_TEXT = 'manage_reminders__text'
    MANAGE_REMINDERS__ENTER_WEEKDAY = 'manage_reminders__weekday'
    MANAGE_REMINDERS__ENTER_TIME = 'manage_reminders__time'


class GetTasksReportData:
    """
    state constants for /get_tasks_report
    """
    BOARD_ID = 'board_id'
    LIST_ID = 'list_id'
    LISTS = 'lists'
    INTRO_TEXT = 'introduction'
    INCLUDE_LABELS = 'include_labels'


class ManageRemindersData:
    """
    state constants for /manager_reminders
    """
    GROUP_CHAT_ID = 'chat_id'
    REMINDER_NAME = 'name'
    REMINDER_TEXT = 'text'
    WEEKDAY_NUM = 'weekday_num'
    WEEKDAY_NAME = 'weekday_name'
    TIME = 'time'


class ButtonValues(Enum):
    """
    Enum for button payload constants.
    """
    GET_TASKS_REPORT__NO_INTRO = 'tasks_report_data__no_intro'
    GET_TASKS_REPORT__LABELS__YES = 'tasks_report_data__labels__yes'
    GET_TASKS_REPORT__LABELS__NO = 'tasks_report_data__labels__no'
    MANAGE_REMINDERS__ACTIONS__NEW = 'tasks_repost__actions__new'
    MANAGE_REMINDERS__ACTIONS__EDIT = 'tasks_repost__actions__edit'
    MANAGE_REMINDERS__ACTIONS__DELETE = 'tasks_repost__actions__delete'
    MANAGE_REMINDERS__MON = '0:Пн'
    MANAGE_REMINDERS__TUE = '1:Вт'
    MANAGE_REMINDERS__WED = '2:Ср'
    MANAGE_REMINDERS__THU = '3:Чт'
    MANAGE_REMINDERS__FRI = '4:Пт'
    MANAGE_REMINDERS__SAT = '5:Сб'
    MANAGE_REMINDERS__SUN = '6:Вс'
