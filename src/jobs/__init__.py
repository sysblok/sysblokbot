"""
A module for business logic-containing regular jobs.
Jobs should use corresponding client objects to interact with
Trello, Spreadsheets or Telegram API.
Jobs can be ran from scheduler or from anywhere else for a one-off action.
"""

from . import config_updater_job
from . import publication_plans_job
from . import sample_job
from . import trello_board_state_job
