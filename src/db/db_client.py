import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import requests
from sqlalchemy import create_engine, desc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from .. import consts
from ..sheets.sheets_client import GoogleSheetsClient
from ..utils.singleton import Singleton
from .db_objects import (
    Author,
    Base,
    Chat,
    Curator,
    Reminder,
    Rubric,
    TeamMember,
    TrelloAnalytics,
)

logger = logging.getLogger(__name__)


class DBClient(Singleton):
    def __init__(self, db_config=None):
        if self.was_initialized():
            return

        self._db_config = db_config
        self._update_from_config()
        logger.info("DBClient successfully initialized")

    def update_config(self, new_db_config: dict):
        """To be called after config automatic update"""
        self._db_config = new_db_config
        self._update_from_config()

    def _update_from_config(self):
        self.engine = create_engine(
            self._db_config["uri"],
            connect_args={"check_same_thread": False},
            echo=False,
        )
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)
        Base.metadata.create_all(self.engine)

    def fetch_all(self, sheets_client: GoogleSheetsClient):
        self.fetch_authors_sheet(sheets_client)
        self.fetch_curators_sheet(sheets_client)
        self.fetch_team_sheet(sheets_client)
        self.fetch_rubrics_sheet(sheets_client)

    def fetch_authors_sheet(self, sheets_client: GoogleSheetsClient):
        session = self.Session()
        try:
            # clean this table
            session.query(Author).delete()
            # re-download it
            authors = sheets_client.fetch_authors()
            for item in authors:
                author = Author.from_sheetfu_item(item)
                session.add(author)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to update authors table from sheet", exc_info=e)
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
            for item in curators:
                curator = Curator.from_sheetfu_item(item)
                session.add(curator)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to update curators table from sheet", exc_info=e)
            session.rollback()
            return 0
        return len(curators)

    def fetch_team_sheet(self, sheets_client: GoogleSheetsClient):
        session = self.Session()
        try:
            # clean this table
            session.query(TeamMember).delete()
            # re-download it
            team = sheets_client.fetch_hr_team()
            for item in team:
                member = TeamMember.from_sheetfu_item(item)
                session.add(member)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to update team table from sheet", exc_info=e)
            session.rollback()
            return 0
        return len(team)

    def fetch_rubrics_sheet(self, sheets_client: GoogleSheetsClient):
        session = self.Session()
        try:
            # clean this table
            session.query(Rubric).delete()
            # re-download it
            rubrics = sheets_client.fetch_rubrics()
            for item in rubrics:
                rubric = Rubric.from_sheetfu_item(item)
                if rubric is None:
                    continue
                session.add(rubric)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to update rubric table from sheet", exc_info=e)
            session.rollback()
            return 0
        return len(rubrics)

    def fill_team_roles(self, member_roles: Dict[str, List[str]]):
        # Set roles for users
        session = self.Session()
        for member_id, roles in member_roles.items():
            update = {TeamMember.roles: json.dumps(roles)}
            session.query(TeamMember).filter(TeamMember.id == member_id).update(update)
        session.commit()

    def find_focalboard_username_by_telegram_username(self, telegram_username: str):
        # TODO: make batch queries
        session = self.Session()
        author = (
            session.query(Author).filter((Author.telegram == telegram_username)).first()
        )
        if author is None:
            logger.warning(f"Focalboard id not found for telegram {telegram_username}")
            return None
        return author.focalboard

    def find_author_telegram_by_trello(self, trello_id: str):
        # TODO: make batch queries
        session = self.Session()
        author = (
            session.query(Author)
            .filter((Author.trello == trello_id) | (Author.focalboard == trello_id))
            .first()
        )
        if author is None:
            logger.warning(f"Telegram id not found for author {trello_id}")
            return None
        return author.telegram

    def get_curator_by_trello_id(self, trello_id: str) -> Curator:
        session = self.Session()
        author = session.query(Author).filter(Author.trello == trello_id).first()
        if author is None or not author.telegram:
            return None
        curator = (
            session.query(Curator)
            .filter(Curator.telegram == author.telegram)
            .filter(Curator.team == "Авторы")
            .first()
        )
        return curator

    def get_curator_by_telegram(self, telegram: str) -> Curator:
        session = self.Session()
        if not telegram.startswith("@"):
            telegram = f"@{telegram}"
        return session.query(Curator).filter(Curator.telegram == telegram).first()

    def get_curator_by_role(self, role: str) -> Curator:
        session = self.Session()
        return session.query(Curator).filter(Curator.role == role).first()

    def find_curators_by_author_trello(self, trello_id: str) -> List[Curator]:
        # TODO: make batch queries
        session = self.Session()
        curators = (
            session.query(Curator)
            .join(Author)
            .filter(Author.trello == trello_id)
            .filter(Curator.team == "Авторы")
            .all()
        )
        if not curators:
            logger.warning(f"Curators not found for author {trello_id}")
        return curators

    def get_rubrics(self) -> List:
        return self.Session().query(Rubric).all()

    def find_curators_by_trello_label(self, trello_label: str) -> List[Curator]:
        # TODO: make batch queries
        session = self.Session()
        curators = (
            session.query(Curator)
            .filter(Curator.trello_labels.contains(trello_label))
            .all()
        )
        if not curators:
            logger.warning(f"Curators not found for label {trello_label}")
        return curators

    def get_all_chats(self) -> List[Chat]:
        session = self.Session()
        return session.query(Chat).all()

    def get_all_members(self) -> List[TeamMember]:
        session = self.Session()
        return session.query(TeamMember).all()

    def get_members_for_role(self, role_name: str) -> List[TeamMember]:
        if not re.match(r"[a-z_]+", role_name):
            logger.warning(f"get_members_for_role: weird role_name: {role_name}")
            return []
        session = self.Session()
        members = (
            session.query(TeamMember)
            .filter(TeamMember.roles.like(f"%{role_name}%"))
            .all()
        )
        return members

    def get_member_by_name(self, member_name: str) -> Optional[TeamMember]:
        if not re.match(r"[А-Яа-я ]+", member_name):
            logger.warning(f"get_member_by_name: weird member_name: {member_name}")
            return None
        session = self.Session()
        members = (
            session.query(TeamMember)
            .filter(TeamMember.name.like(f"%{member_name}%"))
            .all()
        )
        if len(members) > 1:
            logger.warning(
                f"get_member: Name {member_name} fits {len(members)} members"
            )
        return members[0] if members else None

    def set_chat_name(self, chat_id: int, chat_name: str, set_curator: bool = False):
        # Update or set chat name. If chat is known to be curator's, set the flag.
        session = self.Session()
        chat = session.query(Chat).get(chat_id)
        if chat:
            update = {Chat.title: chat_name}
            if set_curator:
                update[Chat.is_curator] = True
            session.query(Chat).filter(Chat.id == chat_id).update(update)
        else:
            session.add(Chat(id=chat_id, title=chat_name, is_curator=set_curator))
        session.commit()

    def get_chat_name(self, chat_id: int) -> str:
        session = self.Session()
        chat = session.query(Chat).filter(Chat.id == chat_id).first()
        if chat is None:
            raise ValueError(f"No chat found with id {chat_id}")
        return chat.title

    def get_chat_by_name(self, chat_name: str) -> Chat:
        """
        Can be used to get chat_id of private chat with the bot by username
        """
        session = self.Session()
        chat = session.query(Chat).filter(Chat.title == chat_name).first()
        return chat

    def get_reminders_by_user_id(
        self, user_chat_id: int
    ) -> List[Tuple[Reminder, Chat]]:
        """
        If user_chat_id is None, shows all reminders
        """
        session = self.Session()
        if user_chat_id is None:
            reminders = session.query(Reminder, Chat).join(Chat).all()
        else:
            reminders = (
                session.query(Reminder, Chat)
                .join(Chat)
                .filter(Reminder.creator_chat_id == user_chat_id)
                .all()
            )
        return reminders

    def get_reminders_to_send(self) -> List[Reminder]:
        session = self.Session()
        now = self._get_now_msk_naive()
        reminders = (
            session.query(Reminder).filter(Reminder.next_reminder_datetime <= now).all()
        )
        # if there's more than 3 hours lag then don't send
        reminders_to_send = [
            reminder
            for reminder in reminders
            if reminder.next_reminder_datetime >= now - timedelta(hours=3)
        ]
        for reminder in reminders:
            next_date = reminder.next_reminder_datetime + timedelta(
                days=reminder.frequency_days
            )
            session.query(Reminder).filter(Reminder.id == reminder.id).update(
                {Reminder.next_reminder_datetime: next_date}
            )
        session.commit()
        return reminders_to_send

    def add_reminder(
        self,
        creator_chat_id: int,
        group_chat_id: int,
        name: str,
        text: str,
        weekday_num: int,
        time: str,
        frequency_days: int = 7,
        send_poll: bool = False,
    ):
        session = self.Session()
        next_reminder = self._make_next_reminder_ts(weekday_num, time)

        session.add(
            Reminder(
                group_chat_id=group_chat_id,
                creator_chat_id=creator_chat_id,
                name=name,
                text=text,
                weekday=weekday_num,
                time=time,
                next_reminder_datetime=next_reminder,
                frequency_days=frequency_days,
                is_active=True,
                send_poll=send_poll,
            )
        )
        session.commit()

    def get_reminder_by_id(self, reminder_id: int) -> Reminder:
        session = self.Session()
        return session.query(Reminder).filter(Reminder.id == reminder_id).first()

    def update_reminder(self, reminder_id: int, **kwargs):
        session = self.Session()
        if "time" in kwargs:
            kwargs["next_reminder_datetime"] = self._make_next_reminder_ts(
                kwargs["weekday"], kwargs["time"]
            )
        if "send_poll" in kwargs:
            kwargs["send_poll"] = bool(kwargs["send_poll"])
        session.query(Reminder).filter(Reminder.id == reminder_id).update(kwargs)
        session.commit()

    def delete_reminder(self, reminder_id: int):
        session = self.Session()
        session.query(Reminder).filter(Reminder.id == reminder_id).delete()
        session.commit()

    @staticmethod
    def _get_now_msk_naive() -> datetime:
        """
        Returns naive (not timezone-aware) datetime object
        representing current time in Europe/Moscow timezone.
        """
        return datetime.now(consts.MSK_TIMEZONE).replace(tzinfo=None)

    @staticmethod
    def _make_next_reminder_ts(weekday_num: int, time: str):
        hour, minute = map(int, time.split(":"))
        today = datetime.today()

        next_reminder = today + timedelta(days=(weekday_num - today.weekday()))
        next_reminder = next_reminder.replace(
            hour=hour,
            minute=minute,
            second=0,
            microsecond=0,
        )
        if next_reminder < DBClient._get_now_msk_naive():
            next_reminder = next_reminder + timedelta(days=7)
        return next_reminder

    def add_item_to_statistics_table(self, statistic: TrelloAnalytics):
        session = self.Session()
        try:
            session.add(statistic)
            session.commit()
        except Exception as e:
            logger.warning(f"Failed to add statistic", exc_info=e)
            session.rollback()

    def get_latest_trello_analytics(self) -> TrelloAnalytics:
        session = self.Session()
        return (
            session.query(TrelloAnalytics).order_by(desc(TrelloAnalytics.date)).first()
        )
