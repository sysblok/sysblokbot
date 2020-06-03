"""App-level constants"""
import os
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

# Upper level config keys
TELEGRAM_CONFIG = 'telegram'
TRELLO_CONFIG = 'trello'
SHEETS_CONFIG = 'sheets'
JOBS_CONFIG = 'jobs'
DB_CONFIG = 'db'

# Jobs-related keys
EVERY = 'every'
AT = 'at'
SEND_TO = 'send_to'


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


# constants for interactive commands (data stored in update.chat_data)
LAST_ACTIONABLE_COMMAND = 'last_actionable_command'
NEXT_ACTION = 'next_action'


class PlainTextUserAction(Enum):
    """
    When adding an item here, go to user_message_handler.py to process it
    """
    # /get_tasks_report items
    ENTER_BOARD_URL = 'get_tasks_report__board_url'
    ENTER_LIST_NUMBER = 'get_tasks_report__list_number'
    ENTER_INTRO = 'get_tasks_report__introduction'


class GetTasksReportData:
    """
    state constants for /get_tasks_report
    """
    BOARD_ID = 'board_id'
    LIST_ID = 'list_id'
    LISTS = 'lists'
    INTRO_TEXT = 'introduction'
    INCLUDE_LABELS = 'include_labels'
