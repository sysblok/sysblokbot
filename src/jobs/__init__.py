"""
A module for business logic-containing regular jobs.
Jobs should use corresponding client objects to interact with
Trello, Spreadsheets or Telegram API.
Jobs can be ran from scheduler or from anywhere else for a one-off action.
"""


from .config_updater_job import ConfigUpdaterJob
from .db_fetch_authors_sheet_job import DBFetchAuthorsSheetJob
from .db_fetch_curators_sheet_job import DBFetchCuratorsSheetJob
from .db_fetch_strings_sheet_job import DBFetchStringsSheetJob
from .editorial_report_job import EditorialReportJob
from .illustrative_report_job import IllustrativeReportJob
from .hr_copy_raw_data_job import HRCopyRawDataJob
from .fill_posts_list_job import FillPostsListJob
from .publication_plans_job import PublicationPlansJob
from .sample_job import SampleJob
from .send_reminders_job import SendRemindersJob
from .trello_board_state_job import TrelloBoardStateJob
from .main_stats_job import TrelloAnalyticsJob
