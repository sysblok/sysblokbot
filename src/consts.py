"""App-level constants"""

import os
from datetime import timedelta, timezone
from enum import Enum
from logging import INFO, WARNING

import telegram

LOG_FORMAT = "%(asctime)s - %(name)s\t- %(levelname)s\t- %(message)s"
USAGE_LOG_LEVEL = (WARNING + INFO) / 2

# Delay to ensure telegram messages come in right order.
MESSAGE_DELAY_SEC = 0.1

COMMIT_URL = (
    f'https://github.com/sysblok/sysblokbot/commit/{os.environ.get("COMMIT_HASH")}'
)
COMMIT_HASH = os.environ.get("COMMIT_HASH_SHORT")
UPTRACE_DSN = os.environ.get("UPTRACE_DSN")


class AppSource(Enum):
    DEFAULT = "manual"
    GITHUB = "prod"
    GITHUB_DEV = "testing"


APP_SOURCE = os.environ.get("APP_SOURCE", AppSource.DEFAULT.value)
TELEGRAM_ERROR_CHAT_ID = os.environ.get("TELEGRAM_ERROR_CHAT_ID", -1)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")

ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CONFIG_PATH = os.path.join(ROOT_DIR, "config.json")
CONFIG_OVERRIDE_PATH = os.path.join(ROOT_DIR, "config_override.json")

CONFIG_RELOAD_MINUTES = 15
MSK_TIMEZONE = timezone(timedelta(hours=3))

# Upper level config keys
TELEGRAM_CONFIG = "telegram"
TRELLO_CONFIG = "trello"
FOCALBOARD_CONFIG = "focalboard"
SHEETS_CONFIG = "sheets"
DRIVE_CONFIG = "drive"
FACEBOOK_CONFIG = "facebook"
DB_CONFIG = "db"
STRINGS_DB_CONFIG = "strings"
JOBS_CONFIG_FILE_KEY = "jobs_config_key"

# Jobs-related keys
EVERY = "every"
AT = "at"
SEND_TO = "send_to"
KWARGS = "kwargs"

# Telegram keys
TELEGRAM_MANAGER_IDS = "manager_chat_ids"

# Trello keys
TRELLO_BOARD_ID = "board_id"

# Vk consts
VK_POST_LINK = "https://vk.com/{group_alias}?w=wall-{group_id}_{post_id}"

# List of keys whose values need to be hidden
REDACTED_KEYS = ("key", "token", "id", "hash", "session")


# Report enum
class ReportPeriod(Enum):
    DAY = "day"
    WEEK = "week"
    DAYS_28 = "days_28"


class TrelloCardColor(Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
    ORANGE = "orange"
    PURPLE = "purple"
    BLUE = "blue"
    SKY = "sky"
    LIME = "lime"
    PINK = "pink"
    BLACK = "black"
    UNKNOWN = "unknown"


class BoardCardColor(Enum):
    BLACK = "propColorGray"
    BROWN = "propColorBrown"
    ORANGE = "propColorOrange"
    YELLOW = "propColorYellow"
    GREEN = "propColorGreen"
    BLUE = "propColorBlue"
    PURPLE = "propColorPurple"
    PINK = "propColorPink"
    RED = "propColorRed"
    UNKNOWN = "unknown"


class TrelloListAlias(Enum):
    TOPIC_SUGGESTION = "trello_list_name__topic_suggestion"
    TOPIC_READY = "trello_list_name__topic_ready"
    IN_PROGRESS = "trello_list_name__in_progress"
    TO_EDITOR = "trello_list_name__to_editor"
    TO_SEO_EDITOR = "trello_list_name__to_seo_editor"
    EDITED_NEXT_WEEK = "trello_list_name__edited_next_week"
    EDITED_SOMETIMES = "trello_list_name__edited_sometimes"
    TO_CHIEF_EDITOR = "trello_list_name__to_chief_editor"
    PROOFREADING = "trello_list_name__proofreading"
    DONE = "trello_list_name__typesetting"
    PUBLISHED = "trello_list_name__published"
    BACK_BURNER = "trello_list_name__back_burner"


class TrelloCustomFieldTypeAlias(Enum):
    AUTHOR = "trello_custom_field__author"
    GOOGLE_DOC = "trello_custom_field__google_doc"
    EDITOR = "trello_custom_field__editor"
    TITLE = "trello_custom_field__post_title"
    ILLUSTRATOR = "trello_custom_field__illustrator"
    COVER = "trello_custom_field__cover"
    WEBSITE = "trello_custom_field__website"
    VKONTAKTE = "trello_custom_field__vk"
    TELEGRAM = "trello_custom_field__telegram"


class TrelloCustomFieldTypes(Enum):
    TEXT = "text"
    CHECKBOX = "checkbox"
    LIST = "list"
    CREATED_AT = "createdTime"
    CREATED_BY = "createdBy"
    SELECT = "select"
    MULTISELECT = "multiSelect"
    MULTIPERSON = "multiPerson"
    DATE = "date"
    URL = "url"


class TrelloCardFieldErrorAlias(Enum):
    BAD_TITLE = "trello_custom_field__post_title"
    BAD_GOOGLE_DOC = "trello_custom_field__google_doc"
    BAD_AUTHORS = "trello_custom_field__author"
    BAD_EDITORS = "trello_custom_field__editor"
    BAD_ILLUSTRATORS = "trello_custom_field__illustrator"
    BAD_COVER = "trello_custom_field__cover"
    BAD_DUE_DATE = "trello_custom_field__due_date"
    BAD_LABEL_NAMES = "trello_custom_field__rubric"


# constants for interactive commands (data stored in update.chat_data)
LAST_ACTIONABLE_COMMAND = "last_actionable_command"
NEXT_ACTION = "next_action"


class PlainTextUserAction(Enum):
    """
    When adding an item here, go to user_message_handler.py to process it
    """

    # /get_tasks_report items
    GET_TASKS_REPORT__ENTER_BOARD_URL = "get_tasks_report__board_url"
    GET_TASKS_REPORT__ENTER_BOARD_NUMBER = "get_tasks_report__board_number"
    GET_TASKS_REPORT__ENTER_LIST_NUMBER = "get_tasks_report__list_number"
    GET_TASKS_REPORT__ENTER_INTRO = "get_tasks_report__introduction"
    GET_TASKS_REPORT__CHOOSE_IF_FILL_LABELS = "get_tasks_report__fill_labels"
    # /manage_reminders items
    MANAGE_REMINDERS__CHOOSE_ACTION = "manage_reminders__action"
    MANAGE_REMINDERS__ENTER_CHAT_ID = "manage_reminders__chat_id"
    MANAGE_REMINDERS__ENTER_NAME = "manage_reminders__name"
    MANAGE_REMINDERS__ENTER_TEXT = "manage_reminders__text"
    MANAGE_REMINDERS__CHOOSE_WEEKDAY = "manage_reminders__weekday"
    MANAGE_REMINDERS__ENTER_TIME = "manage_reminders__time"
    MANAGE_REMINDERS__ENTER_REMINDER_NUMBER = "manage_reminders__reminder_number"
    MANAGE_REMINDERS__DELETE_REQUEST = "manage_reminders__delete"
    MANAGE_REMINDERS__CHOOSE_EDIT_ACTION = "manage_reminders__edit_action"
    MANAGE_REMINDERS__TOGGLE_POLL = "manage_reminders__toggle_poll"
    MANAGE_REMINDERS__SUCCESS = "manage_reminders__success"
    MANAGE_REMINDERS__ENABLE_POLL = "manage_reminders__enable_poll"
    MANAGE_REMINDERS__DISABLE_POLL = "manage_reminders__disable_poll"


class GetTasksReportData:
    """
    state constants for /get_tasks_report
    """

    BOARD_ID = "board_id"
    LIST_ID = "list_id"
    LISTS = "lists"
    INTRO_TEXT = "introduction"
    INCLUDE_LABELS = "include_labels"
    USE_FOCALBOARD = "use_focalboard"


class ManageRemindersData:
    """
    state constants for /manager_reminders
    """

    ACTION_TYPE = "action_type"
    EXISTING_REMINDERS = "existing_reminders_ids"
    CHOSEN_REMINDER_ID = "reminder_id"
    GROUP_CHAT_ID = "chat_id"
    REMINDER_NAME = "name"
    REMINDER_TEXT = "text"
    WEEKDAY_NUM = "weekday_num"
    WEEKDAY_NAME = "weekday_name"
    TIME = "time"


class ButtonValues(Enum):
    """
    Enum for button payload constants.
    """

    MON = "0:Пн"
    TUE = "1:Вт"
    WED = "2:Ср"
    THU = "3:Чт"
    FRI = "4:Пт"
    SAT = "5:Сб"
    SUN = "6:Вс"
    GET_TASKS_REPORT__NO_INTRO = "tasks_report_data__no_intro"
    GET_TASKS_REPORT__LABELS__YES = "tasks_report_data__labels__yes"
    GET_TASKS_REPORT__LABELS__NO = "tasks_report_data__labels__no"
    MANAGE_REMINDERS__ACTIONS__NEW = "tasks_repost__actions__new"
    MANAGE_REMINDERS__ACTIONS__EDIT = "tasks_repost__actions__edit"
    MANAGE_REMINDERS__ACTIONS__DELETE = "tasks_repost__actions__delete"
    MANAGE_REMINDERS__DELETE__YES = "manage_reminders__delete__yes"
    MANAGE_REMINDERS__DELETE__NO = "manage_reminders__delete__no"
    MANAGE_REMINDERS__EDIT__TEXT = "manage_reminders__edit__text"
    MANAGE_REMINDERS__EDIT__TITLE = "manage_reminders__edit__title"
    MANAGE_REMINDERS__EDIT__DATETIME = "manage_reminders__edit__datetime"
    MANAGE_REMINDERS__EDIT__CHAT = "manage_reminders__edit__chat"
    MANAGE_REMINDERS__EDIT__SUSPEND = "manage_reminders__edit__suspend"
    MANAGE_REMINDERS__EDIT__RESUME = "manage_reminders__edit__resume"
    MANAGE_REMINDERS__POLL__YES = "manage_reminders__handler_poll__yes_btn"
    MANAGE_REMINDERS__POLL__NO = "manage_reminders__handler_poll__no_btn"
    MANAGE_REMINDERS__TOGGLE_POLL__YES = "manage_reminders_handler__toggle_poll_yes_btn"
    MANAGE_REMINDERS__TOGGLE_POLL__NO = "manage_reminders_handler__toggle_poll_yes_btn"
    MANAGE_REMINDERS__DISABLE_POLL = "manage_reminders_handler__disable_poll"
    MANAGE_REMINDERS__DISABLE_POLL__YES = (
        "manage_reminders_handler__disable_poll_yes_btn"
    )
    MANAGE_REMINDERS__ENABLE_POLL = "manage_reminders_handler__enable_poll_btn"
    MANAGE_REMINDERS__ENABLE_POLL__YES = "manage_reminders_handler__enable_poll_yes_btn"


WEEKDAYS_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]

WEEKDAY_BUTTONS = [
    [
        telegram.InlineKeyboardButton("Пн", callback_data=ButtonValues.MON.value),
        telegram.InlineKeyboardButton("Вт", callback_data=ButtonValues.TUE.value),
        telegram.InlineKeyboardButton("Ср", callback_data=ButtonValues.WED.value),
        telegram.InlineKeyboardButton("Чт", callback_data=ButtonValues.THU.value),
        telegram.InlineKeyboardButton("Пт", callback_data=ButtonValues.FRI.value),
        telegram.InlineKeyboardButton("Сб", callback_data=ButtonValues.SAT.value),
        telegram.InlineKeyboardButton("Вc", callback_data=ButtonValues.SUN.value),
    ]
]


class CommandCategories(Enum):
    """
    Enum for /help command sections string aliases.
    """

    MOST_USED = "help__00_most_used"
    DATA_SYNC = "help__01_synchronize"
    CONFIG = "help__02_config"
    BROADCAST = "help__03_broadcast"
    LOGGING = "help__04_logging"
    SUMMARY = "help__05_summary"
    STATS = "help__06_stats"
    REGISTRY = "help__07_registry"
    REMINDERS = "help__08_reminders"
    HR = "help__09_hr"
    DEBUG = "help__10_debug"
