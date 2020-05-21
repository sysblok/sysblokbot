import logging
import requests

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .db_objects import Author, Base
from ..sheets.sheets_client import GoogleSheetsClient
from ..utils.singleton import Singleton


logger = logging.getLogger(__name__)


class DBClient(Singleton):
    def __init__(self, config=None):
        if self.was_initialized():
            return

        self._db_config = config
        self._update_from_config()
        logger.info('DBClient successfully initialized')

    def _update_from_config(self):
        self.engine = create_engine(self._db_config['uri'], echo=True)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        Base.metadata.create_all(self.engine)

    def fetch_authors_sheet(self, sheets_client: GoogleSheetsClient):
        try:
            # clean this table
            self.session.query(Author).delete()
            # re-download it
            authors = sheets_client.fetch_authors()
            for author_dict in authors:
                author = Author.from_dict(author_dict)
                self.session.add(author)
            self.session.commit()
        except Exception as e:
            logger.warning(f"Failed to update authors table from sheer: {e}")
            self.session.rollback()
        return len(authors)

    def find_author_telegram_id_by_trello_id(self, trello_id):
        author = self.session.query(Author).filter(
            Author.trello == trello_id
        ).first()
        if author is None:
            logger.warning(f'Telegram id not found for {trello_id}')
            return None
        return author.telegram
