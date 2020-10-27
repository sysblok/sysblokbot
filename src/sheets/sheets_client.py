import logging
from pprint import pprint
from typing import List, Dict, Optional

from sheetfu import SpreadsheetApp, Table

from .sheets_objects import RegistryPost, TableProxy
from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)

UNDEFINED_STATES = ('', '-', '#N/A')


class GoogleSheetsClient(Singleton):
    def __init__(self, sheets_config: dict):
        if self.was_initialized():
            return

        self._sheets_config = sheets_config
        self._update_from_config()
        logger.info('GoogleSheetsClient successfully initialized')

    def update_config(self, new_sheets_config: dict):
        """To be called after config automatic update"""
        self._sheets_config = new_sheets_config
        self._update_from_config()

    def _update_from_config(self):
        """Update attributes according to current self._sheets_config"""
        self.authors_sheet_key = self._sheets_config['authors_sheet_key']
        self.curators_sheet_key = self._sheets_config['curators_sheet_key']
        self.post_registry_sheet_key = self._sheets_config['post_registry_sheet_key']
        self.rubrics_registry_sheet_key = self._sheets_config['rubrics_registry_sheet_key']
        self.strings_sheet_key = self._sheets_config['strings_sheet_key']
        self.team_sheet_key = self._sheets_config['team_sheet_key']
        self._authorize()

    def _authorize(self):
        self.client = SpreadsheetApp(self._sheets_config['api_key_path'])

    def fetch_authors(self) -> List[Dict]:
        title_key_map = {
            "Как вас зовут?": "name",
            "Куратор (как автора)": "curator",
            "Статус": "status",
            "Телеграм": "telegram",
            "Трелло": "trello",
        }
        return self._parse_gs_res(title_key_map, self.authors_sheet_key, 'Кураторы и контакты')

    def fetch_curators(self) -> List[Dict]:
        title_key_map = {
            "Имя": "name",
            "Роль": "role",
            "Команда": "team",
            "Рубрика/Рубрики": "section",
            "Название рубрики в трелло": "trello_labels",
            "Телеграм": "telegram",
        }
        return self._parse_gs_res(title_key_map, self.curators_sheet_key)

    def fetch_rubrics(self) -> List[Dict]:
        title_key_map = {
            "Название рубрики ": "name",  # space is important!
            "Тег вк": "vk_tag",
            "Тег в тг": "tg_tag",
        }
        return self._parse_gs_res(title_key_map, self.rubrics_registry_sheet_key)

    def fetch_strings(self) -> List[Dict]:
        title_key_map = {
            "Идентификатор строки": "id",
            "Сообщение": "value",
        }
        return self._parse_gs_res(title_key_map, self.strings_sheet_key)
    
    def fetch_team_raw(self) -> List[Dict]:
        title_key_map = {
            "Отметка времени": "timestamp",
            "Как вас зовут? (лучше имя + фамилия)": "name",
            "Чем бы вам было интересно заниматься в проекте?": "interests",
            "Другие контактные данные (ссылка на соц.сети/почта)": "contacts",
            "Расскажите о себе": "about",
            "Ссылка на телеграм (со значком @)": "telegram",
            "Статус": "status",
        }
        return self._parse_gs_res(title_key_map, self.team_sheet_key, 'Анкеты')

    def update_posts_registry(self, entries: List[RegistryPost]):
        sheet = self._open_by_key(self.post_registry_sheet_key)
        data = sheet.get_sheet_by_id(0).get_data_range()
        table = TableProxy(data, {
        'name': 'Название поста',
        'author': 'Автор',
        'rubric_1': 'Рубрика',
        'rubric_2': 'Доп.Рубрика',
        'google_doc': 'Гугл.док',
        'trello': 'Trello',
        'editor': 'Редактор',
        'cover_type': 'Тип обложки',
        'cover': 'Обложка',
        'illustrator': 'Иллюстратор',
        'date_site': 'Дата (сайт)',
        'status_site': 'Статус публикации (сайт)',
        'pin_site': '📌',
    })
        new_posts = []
        try:
            for entry in entries:
                if self._has_string(data, entry.trello_url):
                    logger.info(f'Card {entry.trello_url} already present in registry')
                    continue
                table.add_one(entry.to_dict())
                new_posts.append(entry.title)
            table.commit()
        except Exception as e:
            logger.error(f'Failed to update post registry: {e}')
        return new_posts

    def _has_string(self, data, string: str):
        return string in str(data.get_values())

    def _parse_gs_res(
            self, title_key_map: Dict, sheet_key: str, sheet_name: str = ''
    ) -> List[Dict]:
        titles, *rows = self._get_sheet_values(sheet_key, sheet_name)
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

    def _get_sheet_values(self, sheet_key: str, sheet_name: str = '') -> List:
        sheet = self._open_by_key(sheet_key)
        worksheet = (
            sheet.get_sheet_by_name(sheet_name) if sheet_name != '' else sheet.get_sheet_by_id(0)
        )
        return worksheet.get_data_range().get_values()

    def _open_by_key(self, sheet_key: str):
        try:
            return self.client.open_by_id(sheet_key)
        except Exception as e:
            logger.error(f'Failed to access sheet {sheet_key}: {e}')

    @classmethod
    def _parse_cell_value(cls, value: str) -> Optional[str]:
        if value in UNDEFINED_STATES:
            return None
        return str(value)
