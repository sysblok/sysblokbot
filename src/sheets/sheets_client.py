import logging
from pprint import pprint
from typing import Dict, List, Optional

from sheetfu import SpreadsheetApp, Table
from sheetfu.model import Sheet

from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)


class GoogleSheetsClient(Singleton):
    def __init__(self, sheets_config: dict):
        if self.was_initialized():
            return

        self._sheets_config = sheets_config
        self._update_from_config()
        logger.info("GoogleSheetsClient successfully initialized")

    def update_config(self, new_sheets_config: dict):
        """To be called after config automatic update"""
        self._sheets_config = new_sheets_config
        self._update_from_config()

    def _update_from_config(self):
        """Update attributes according to current self._sheets_config"""
        self.authors_sheet_key = self._sheets_config["authors_sheet_key"]
        self.curators_sheet_key = self._sheets_config["curators_sheet_key"]
        self.hr_sheet_key = self._sheets_config["hr_sheet_key"]
        self.hr_pt_sheet_key = self._sheets_config["hr_pt_sheet_key"]
        self.post_registry_sheet_key = self._sheets_config["post_registry_sheet_key"]
        self.rubrics_registry_sheet_key = self._sheets_config[
            "rubrics_registry_sheet_key"
        ]
        self.strings_sheet_key = self._sheets_config["strings_sheet_key"]
        self._authorize()

    def _authorize(self):
        self.client = SpreadsheetApp(self._sheets_config["api_key_path"])

    def fetch_authors(self) -> Table:
        return self._fetch_table(self.authors_sheet_key, "Кураторы и контакты")

    def fetch_curators(self) -> Table:
        return self._fetch_table(self.curators_sheet_key)

    def fetch_rubrics(self) -> Table:
        return self._fetch_table(self.rubrics_registry_sheet_key)

    def fetch_strings(self) -> Table:
        return self._fetch_table(self.strings_sheet_key)

    def fetch_hr_forms_raw(self) -> Table:
        return self._fetch_table(self.hr_sheet_key, "Ответы на форму")

    def fetch_hr_forms_processed(self) -> Table:
        return self._fetch_table(self.hr_sheet_key, "Анкеты")

    def fetch_hr_pt_forms_raw(self) -> Table:
        return self._fetch_table(self.hr_pt_sheet_key, "Ответы Главный сайт")

    def fetch_hr_pt_forms_processed(self) -> Table:
        return self._fetch_table(self.hr_pt_sheet_key, "Анкеты")

    def fetch_hr_team(self) -> Table:
        return self._fetch_table(self.hr_sheet_key, "Команда (с заморозкой)")

    def fetch_posts_registry(self) -> Table:
        return self._fetch_table(self.post_registry_sheet_key)

    def update_posts_registry(self, entries):
        sheet = self._open_by_key(self.post_registry_sheet_key)
        data = sheet.get_sheet_by_id(0).get_data_range()
        table = Table(data)
        new_posts = []
        try:
            for entry in entries:
                if self._has_string(data, entry.trello_url):
                    logger.info(f"Card {entry.trello_url} already present in registry")
                    continue
                table.add_one(entry.to_dict())
                new_posts.append(entry.title)
            table.commit()
        except Exception as e:
            logger.error(f"Failed to update post registry: {e}")
        return new_posts

    def fetch_sheet(self, sheet_key: str, sheet_name: Optional[str] = None) -> Sheet:
        sheet = self._open_by_key(sheet_key)
        return (
            sheet.get_sheet_by_name(sheet_name)
            if sheet_name
            else sheet.get_sheet_by_id(0)
        )

    def _has_string(self, data, string: str):
        return string in str(data.get_values())

    def _fetch_table(self, sheet_key: str, sheet_name: Optional[str] = None) -> Table:
        worksheet = self.fetch_sheet(sheet_key, sheet_name)
        return Table(worksheet.get_data_range())

    def _open_by_key(self, sheet_key: str):
        try:
            return self.client.open_by_id(sheet_key)
        except Exception as e:
            logger.error(f"Failed to access sheet {sheet_key}: {e}")
            raise
