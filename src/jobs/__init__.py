"""
A module for business logic-containing regular jobs.
Jobs should use corresponding client objects to interact with
Trello, Spreadsheets or Telegram API.
Jobs can be ran from scheduler or from anywhere else for a one-off action.
"""


from .config_updater_job import ConfigUpdaterJob
from .publication_plans_job import PublicationPlansJob
from .sample_job import SampleJob
from .trello_board_state_job import TrelloBoardStateJob
