import logging
import requests
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from .db_objects import DBAuthor, Base, DBCurator, DBTrelloList, DBTrelloCustomFieldType
from ..consts import TrelloListAlias, TrelloCustomFieldTypeAlias
from ..sheets.sheets_client import GoogleSheetsClient
from ..trello.trello_client import TrelloClient
from ..utils.singleton import Singleton


logger = logging.getLogger(__name__)


class DBClient(Singleton):
    def __init__(self, config=None):
        if self.was_initialized():
            return

        self._db_config = config
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
            session.query(DBAuthor).delete()
            # re-download it
            authors = sheets_client.fetch_authors()
            for author_dict in authors:
                author = DBAuthor.from_dict(author_dict)
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
            session.query(DBCurator).delete()
            # re-download it
            curators = sheets_client.fetch_curators()
            for curator_dict in curators:
                curator = DBCurator.from_dict(curator_dict)
                session.add(curator)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to update curators table from sheet: {e}")
            session.rollback()
            return 0
        return len(curators)

    def fetch_trello_list_ids(self, trello_client: TrelloClient):
        session = self.Session()
        try:
            # clean this table
            session.query(DBTrelloList).delete()
            # re-download it
            lists = trello_client.get_lists()
            for lst in lists:
                trello_lst = DBTrelloList()
                trello_lst.alias = DBClient._get_alias(lst, TrelloListAlias)
                if trello_lst.alias is None:
                    continue
                trello_lst.board_id = trello_client.board_id
                trello_lst.name = lst.name
                trello_lst.list_id = lst.id
                session.add(trello_lst)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to update lists from Trello: {e}")
            session.rollback()
            return 0
        return len(lists)

    def get_list_ids_by_aliases(self, aliases: List[TrelloListAlias]):
        # TODO: make batch queries
        session = self.Session()
        result = []
        for alias in aliases:
            lst = session.query(DBTrelloList).filter(
                DBTrelloList.alias == alias.value
            ).first()
            if lst is None:
                logger.warning(f'Trello list id not found for alias {alias}')
                result.append(None)
            else:
                result.append(lst.list_id)
        return result

    @classmethod
    def _get_alias(cls, item, alias_enum):
        for alias in alias_enum:
            if item.name.startswith(alias.value):
                return alias.value
        return None

    def fetch_trello_custom_field_types(self, trello_client: TrelloClient):
        session = self.Session()
        try:
            # clean this table
            session.query(DBTrelloCustomFieldType).delete()
            # re-download it
            types = trello_client.get_board_custom_field_types()
            for typ in types:
                field_type = DBTrelloCustomFieldType()
                field_type.alias = DBClient._get_alias(typ, TrelloCustomFieldTypeAlias)
                if field_type.alias is None:
                    continue
                field_type.board_id = trello_client.board_id
                field_type.name = typ.name
                field_type.id = typ.id
                field_type.value_type = typ.type.value
                session.add(field_type)
            session.commit()
        except Exception as e:
            logger.error(f"Failed to update custom field types from Trello: {e}")
            session.rollback()
            return 0
        return len(types)

    def get_all_custom_field_types(self):
        session = self.Session()
        return session.query(DBTrelloCustomFieldType).all()

    def get_custom_field_type_by_alias(self, alias: TrelloCustomFieldTypeAlias):
        session = self.Session()
        return session.query(DBTrelloCustomFieldType).filter(
            DBTrelloCustomFieldType.alias == alias.value
        ).first()

    def get_custom_field_type_by_id(self, type_id: str):
        session = self.Session()
        return session.query(DBTrelloCustomFieldType).filter(
            DBTrelloCustomFieldType.id == type_id
        ).first()

    def find_author_telegram_by_trello(self, trello_id: str):
        # TODO: make batch queries
        session = self.Session()
        author = session.query(DBAuthor).filter(
            DBAuthor.trello == trello_id
        ).first()
        if author is None:
            logger.warning(f'Telegram id not found for author {trello_id}')
            return None
        return author.telegram

    def find_curators_by_author_trello(self, trello_id: str) -> List[DBCurator]:
        # TODO: make batch queries
        session = self.Session()
        curators = session.query(DBCurator).join(DBAuthor).filter(
            DBAuthor.trello == trello_id
        ).all()
        if not curators:
            logger.warning(f'Curators not found for author {trello_id}')
        return curators

    def find_curators_by_trello_label(self, trello_label: str) -> List[DBCurator]:
        # TODO: make batch queries
        session = self.Session()
        curators = session.query(DBCurator).filter(
            DBCurator.trello_labels.contains(trello_label)
        ).all()
        if not curators:
            logger.warning(f'Curators not found for label {trello_label}')
        return curators
