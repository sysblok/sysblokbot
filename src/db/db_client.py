import logging
import requests
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from .db_objects import Author, Base, Chat, Curator
from ..sheets.sheets_client import GoogleSheetsClient
from ..utils.singleton import Singleton


logger = logging.getLogger(__name__)


class DBClient(Singleton):
    def __init__(self, db_config=None):
        if self.was_initialized():
            return

        self._db_config = db_config
        self._update_from_config()
        logger.info('DBClient successfully initialized')

    def update_config(self, new_db_config: dict):
        """To be called after config automatic update"""
        self._db_config = new_db_config
        self._update_from_config()

    def _update_from_config(self):
        self.engine = create_engine(
            self._db_config['uri'],
            connect_args={'check_same_thread': False},
            echo=True,
        )
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)
        Base.metadata.create_all(self.engine)

    def fetch_all(self, sheets_client: GoogleSheetsClient):
        self.fetch_authors_sheet(sheets_client)
        self.fetch_curators_sheet(sheets_client)

    def fetch_authors_sheet(self, sheets_client: GoogleSheetsClient):
        session = self.Session()
        try:
            # clean this table
            session.query(Author).delete()
            # re-download it
            authors = sheets_client.fetch_authors()
            for author_dict in authors:
                author = Author.from_dict(author_dict)
                session.add(author)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to update authors table from sheet: {e}")
            session.rollback()
            return 0
        return len(authors)

    def fetch_curators_sheet(self, sheets_client: GoogleSheetsClient):
        session = self.Session()
        try:
            # clean this table
            session.query(Curator).delete()
            # re-download it
            curators = sheets_client.fetch_curators()
            for curator_dict in curators:
                curator = Curator.from_dict(curator_dict)
                session.add(curator)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to update curators table from sheet: {e}")
            session.rollback()
            return 0
        return len(curators)

    def find_author_telegram_by_trello(self, trello_id: str):
        # TODO: make batch queries
        session = self.Session()
        author = session.query(Author).filter(
            Author.trello == trello_id
        ).first()
        if author is None:
            logger.warning(f'Telegram id not found for author {trello_id}')
            return None
        return author.telegram

    def find_curators_by_author_trello(self, trello_id: str) -> List[Curator]:
        # TODO: make batch queries
        session = self.Session()
        curators = session.query(Curator).join(Author).filter(
            Author.trello == trello_id
        ).all()
        if not curators:
            logger.warning(f'Curators not found for author {trello_id}')
        return curators

    def find_curators_by_trello_label(self, trello_label: str) -> List[Curator]:
        # TODO: make batch queries
        session = self.Session()
        curators = session.query(Curator).filter(
            Curator.trello_labels.contains(trello_label)
        ).all()
        if not curators:
            logger.warning(f'Curators not found for label {trello_label}')
        return curators

    def set_chat_name(self, chat_id: int, chat_name: str):
        session = self.Session()
        chat = session.query(Chat).get(chat_id)
        if chat:
            session.query(Chat).filter(Chat.id == chat_id).update({Chat.name: chat_name})
        else:
            session.add(Chat(id=chat_id, name=chat_name))
        session.commit()
