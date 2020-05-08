import logging
from pprint import pprint
from typing import List, Dict, Optional

from ..utils.singleton import Singleton
import gspread
from google.oauth2.service_account import Credentials

from .sheets_objects import RegistryPost

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
        self.post_registry_sheet_key = self._sheets_config['post_registry_sheet_key']
        self.rubrics_registry_sheet_key = self._sheets_config['rubrics_registry_sheet_key']

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
            if curator['role'].strip() == author['curator'].strip():
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
            if curator['role'].strip() == author['curator'].strip():
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

    def fetch_rubrics_registry(self) -> List[Dict]:
        title_key_map = {
            "Название рубрики ": "name",  # space is important!
            "Тег вк": "vk_tag",
            "Тег в тг": "tg_tag",
        }
        return self._parse_gs_res(title_key_map, self.rubrics_registry_sheet_key)

    def update_posts_registry(self, entries: List[RegistryPost]):
        sheet = self.client.open_by_key(self.post_registry_sheet_key)
        worksheet = sheet.get_worksheet(0)
        num_of_posts = len(worksheet.get_all_values()) - 2  # table formatting
        logger.info(f'Posts registry currently has {num_of_posts} posts')
        # TODO(alexeyqu): move this to DB and sync it
        rubrics_registry = self.fetch_rubrics_registry()
        new_data = []
        count_updated = 0
        for entry in entries:
            if self._has_string(worksheet, entry.trello_url):
                logger.info(f'Card {entry.trello_url} already present in registry')
                continue
            this_line = num_of_posts + count_updated + 3  # table formatting
            rubric_1 = next(
                (rubric['vk_tag'] for rubric in rubrics_registry
                if rubric['name'] == entry.rubrics[0]), 'нет'
            )
            rubric_2 = 'нет'
            if len(entry.rubrics) > 1:
                rubric_2 = next(
                    (rubric['vk_tag'] for rubric in rubrics_registry
                    if rubric['name'] == entry.rubrics[1]), 'нет'
                )
            if entry.is_archive_post:
                new_data.append([
                    this_line - 2,
                    entry.title,
                    entry.authors,
                    rubric_1,
                    rubric_2,
                    entry.google_doc,
                    entry.trello_url,
                    entry.editors,
                    None,  # Оценка редактора
                    None,  # План по контенту
                    'нет',  # Тип обложки
                    'нет',  # Обложка
                    'нет',  # Иллюстратор
                    'нет',  # Дата (сайт)
                    'архив',  # Статус публикации (сайт)
                    'нет',  # Pin post
                ])
            else:
                new_data.append([
                    this_line - 2,
                    entry.title,
                    entry.authors,
                    rubric_1,
                    rubric_2,
                    entry.google_doc,
                    entry.trello_url,
                    entry.editors,
                    None,  # Оценка редактора
                    None,  # План по контенту
                    None,  # Тип обложки
                    None,  # Обложка
                    entry.illustrators,
                    None,  # Дата (сайт)
                    None,  # Статус публикации (сайт)
                    'да' if entry.is_main_post else 'нет',
                ])
            count_updated += 1
        try:  
            worksheet.update(
                f'A{num_of_posts + 3}:P{num_of_posts + count_updated + 3}',
                new_data
            )
        except Exception as e:
            logger.error(f'Failed to update post registry: {e}')
        num_of_posts_after = len(worksheet.get_all_values()) - 2  # table formatting
        assert num_of_posts_after == num_of_posts + count_updated
        return count_updated, num_of_posts, num_of_posts_after

    def _has_string(self, worksheet, string: str):
        try:
            worksheet.find(string)
        except gspread.exceptions.CellNotFound:
            return False
        return True

    def _parse_gs_res(self, title_key_map: Dict, sheet_key: str) -> List[Dict]:
        titles, *rows = self._get_sheet_values(sheet_key)
        title_idx_map = {
            idx: title_key_map[title]
            for idx, title in enumerate(titles)
            if title in title_key_map
        }
        res = []
        for row in rows:
            item = {
                title_idx_map[key]: self._parse_cell_value(val)
                for key, val in enumerate(row)
                if key in title_idx_map
            }
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
