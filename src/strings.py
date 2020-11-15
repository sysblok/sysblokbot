from collections import defaultdict
import logging
from typing import List, Tuple

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from . import consts
from .sheets.sheets_client import GoogleSheetsClient
from .utils.singleton import Singleton

from sqlalchemy import Column, String


logger = logging.getLogger(__name__)
Base = declarative_base()


class DBString(Base):
    __tablename__ = 'strings'
    id = Column(String, primary_key=True)
    value = Column(String)

    def __init__(self, id, value):
        self.id = id
        self.value = value


class StringsDBClient(Singleton):
    def __init__(self, strings_db_config=None):
        if self.was_initialized():
            return

        self._strings_db_config = strings_db_config
        self._update_from_config()
        logger.info('StringDBClient successfully initialized')

    def update_config(self, new_strings_db_config: dict):
        """To be called after config automatic update"""
        self._strings_db_config = new_strings_db_config
        self._update_from_config()

    def _update_from_config(self):
        self.engine = create_engine(
            self._strings_db_config['uri'],
            connect_args={'check_same_thread': False},
            echo=True,
        )
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)
        Base.metadata.create_all(self.engine)

    def fetch_strings_sheet(self, sheets_client: GoogleSheetsClient):
        session = self.Session()
        try:
            # clean this table
            session.query(DBString).delete()
            # re-download it
            strings = sheets_client.fetch_strings()
            for item in strings:
                string_id = item.get_field_value('Id')
                if string_id is None:
                    # we use that to separate different strings
                    continue
                string_value = item.get_field_value('Message')
                string = DBString(string_id, string_value)
                if string is None:
                    continue
                session.add(string)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to update string table from sheet: {e}")
            session.rollback()
            return 0
        return len(strings)

    def get_string(self, string_id: str) -> str:
        session = self.Session()
        message = session.query(DBString).filter(
            DBString.id == string_id
        ).first()
        if not message:
            logger.error(f'Message not found for id {string_id}')
            return f'<{string_id}>'
        return message.value


def load(string_id: str, **kwargs) -> str:
    db_client = StringsDBClient()
    return db_client.get_string(string_id).format_map(defaultdict(lambda: '?', kwargs)).strip()
