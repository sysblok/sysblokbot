import logging
from pprint import pprint
from typing import List, Dict, Optional

from ..utils.singleton import Singleton
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

UNDEFINED_STATES = ('', '-', '#N/A')
scope = (
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
)


class GoogleSheetsClient(Singleton):
    def __init__(self, config: dict):
        if self.was_initialized():
            return

        self._sheets_config = config
        self._update_from_config()
        logger.info('GoogleSheetsClient successfully initialized')

    def update_config(self, new_sheets_config: dict):
        """To be called after config automatic update"""
        self._sheets_config = new_sheets_config
        self._update_from_config()

    def _update_from_config(self):
        """Update attributes according to current self._sheets_config"""
        self._credentials = Credentials.from_service_account_file(
            self._sheets_config['api_key_path'], scopes=scope)
        self.client = gspread.authorize(self._credentials)
        self.authors_sheet_key = self._sheets_config['authors_sheet_key']
        self.curators_sheet_key = self._sheets_config['curators_sheet_key']

    def find_author_curators(
            self,
            find_by: str,
            val: str
    ) -> Optional[List[Dict]]:
        authors = self.fetch_authors()
        author = next(
            (author for author in authors if author[find_by] == val), None)
        if author is None:
            return

        curators = self.fetch_curators()
        found_curators = []
        for curator in curators:
            if curator['section'] in author['curator']:
                found_curators.append(curator)
        return found_curators

    def find_curator_authors(
            self,
            find_by: str,
            val: str
    ) -> Optional[List[Dict]]:
        curators = self.fetch_curators()
        curator = next(
            (curator for curator in curators if curator[find_by] == val), None)
        if curator is None:
            return

        authors = self.fetch_authors()
        found_authors = []
        for author in authors:
            if curator['section'] in author['curator']:
                found_authors.append(curator)
        return found_authors

    def find_telegram_id_by_trello_id(self, trello: str) -> Optional[str]:
        authors = self.fetch_authors()
        return next(
            (author['telegram']
                for author in authors if author['trello'] == trello),
            None
        )

    def find_trello_id_by_telegram_id(self, telegram: str) -> Optional[str]:
        authors = self.fetch_authors()
        return next(
            (author['telegram']
                for author in authors if author['trello'] == telegram),
            None
        )

    def fetch_authors(self) -> List[Dict]:
        title_key_map = {
            "Как вас зовут?": "name",
            "Куратор (как автора)": "curator",
            "Статус": "status",
            "Телеграм": "telegram",
            "Трелло": "trello",
        }
        return self._parse_gs_res(title_key_map, self.authors_sheet_key)

    def fetch_curators(self) -> List[Dict]:
        title_key_map = {
            "Имя": "name",
            "Роль": "role",
            "Команда": "team",
            "Рубрика/Рубрики": "section",
            "Название рубрики в трелло": "trello_section",
            "Телеграм": "telegram",
        }
        return self._parse_gs_res(title_key_map, self.curators_sheet_key)

    def _parse_gs_res(self, title_key_map: Dict, sheet_key: str) -> List[Dict]:
        titles, *rows = self._get_sheet_values(sheet_key)
        for title in titles:
            if title not in title_key_map.keys():
                logger.error(f'Update title_key_map. "{title}" caused error.')
        title_idx_map = {idx: title_key_map[title]
                         for idx, title in enumerate(titles)}

        res = []
        for row in rows:
            item = {title_idx_map[key]: self._parse_cell_value(
                val) for key, val in enumerate(row)}
            res.append(item)
        return res

    def _get_sheet_values(self, sheet_key: str) -> List:
        sheet = self.client.open_by_key(sheet_key)
        worksheet = sheet.get_worksheet(0)
        return worksheet.get_all_values()

    @classmethod
    def _parse_cell_value(cls, value: str) -> Optional[str]:
        if value in UNDEFINED_STATES:
            return None
        return value
