from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base

from ..strings import load

Base = declarative_base()


class Author(Base):
    __tablename__ = 'authors'

    name = Column(String, primary_key=True)
    curator = Column(String)
    status = Column(String)
    telegram = Column(String)
    trello = Column(String)

    def __repr__(self):
        return f'Author {self.name} tg={self.telegram} trello={self.trello}'

    @classmethod
    def from_dict(cls, data):
        author = cls()
        author.name = _get_str_data_item(data, 'name')
        author.curator = _get_str_data_item(data, 'curator')
        author.status = _get_str_data_item(data, 'status')
        author.telegram = _get_str_data_item(data, 'telegram')
        author.trello = _get_str_data_item(data, 'trello')
        return author

    def to_dict(self):
        return {
            'name': self.name,
            'curator': self.curator,
            'status': self.status,
            'telegram': self.telegram,
            'trello': self.trello,
        }

    @classmethod
    def from_sheetfu_item(cls, item):
        author = cls()
        author.name = item.get_field_value(load('sheets__what_is_your_name'))
        author.curator = item.get_field_value(load('sheets__curator_as_author'))
        author.status = item.get_field_value(load('sheets__status'))
        author.telegram = item.get_field_value(load('sheets__telegram'))
        author.trello = item.get_field_value(load('sheets__trello'))
        return author


class Curator(Base):
    __tablename__ = 'curators'

    role = Column(String, ForeignKey('authors.curator'), primary_key=True)  # e.g. "Куратор NLP 1"
    name = Column(String, primary_key=True)
    telegram = Column(String)
    team = Column(String)  # e.g. "Авторы"
    section = Column(String)  # e.g. "NLP"
    trello_labels = Column(String)  # e.g. "NLP,Теорлингв"

    def __repr__(self):
        return f'Curator {self.name} tg={self.telegram} section={self.section}'

    @classmethod
    def from_dict(cls, data):
        curator = cls()
        curator.name = _get_str_data_item(data, 'name')
        curator.telegram = _get_str_data_item(data, 'telegram')
        curator.team = _get_str_data_item(data, 'team')
        curator.role = _get_str_data_item(data, 'role')
        curator.section = _get_str_data_item(data, 'section')
        curator.trello_labels = _get_str_data_item(data, 'trello_labels')
        return curator

    def to_dict(self):
        return {
            'name': self.name,
            'telegram': self.telegram,
            'team': self.team,
            'role': self.role,
            'section': self.section,
            'trello_labels': self.trello_labels,
        }

    @classmethod
    def from_sheetfu_item(cls, item):
        curator = cls()
        curator.name = item.get_field_value(load('sheets__name'))
        curator.telegram = item.get_field_value(load('sheets__telegram'))
        curator.team = item.get_field_value(load('sheets__team'))
        curator.role = item.get_field_value(load('sheets__role'))
        curator.section = item.get_field_value(load('sheets__rubric'))
        curator.trello_labels = item.get_field_value(load('sheets__rubric_trello_name'))
        return curator


class TeamMember(Base):
    __tablename__ = 'team'

    id = Column(String, primary_key=True)
    name = Column(String)
    status = Column(String)
    curator = Column(String)
    manager = Column(String)
    telegram = Column(String)
    trello = Column(String)
    role = Column(String)

    def __repr__(self):
        return f'Team member {self.name} tg={self.telegram}'

    @classmethod
    def from_dict(cls, data):
        member = cls()
        member.id = _get_str_data_item(data, 'id')
        member.name = _get_str_data_item(data, 'name')
        member.status = _get_str_data_item(data, 'status')
        member.curator = _get_str_data_item(data, 'curator')
        member.manager = _get_str_data_item(data, 'manager')
        member.telegram = _get_str_data_item(data, 'telegram')
        member.trello = _get_str_data_item(data, 'trello')
        return member

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'status': self.status,
            'curator': self.curator,
            'manager': self.manager,
            'telegram': self.telegram,
            'trello': self.trello,
            'role': self.role,
        }

    @classmethod
    def from_sheetfu_item(cls, item):
        member = cls()
        member.id = item.get_field_value(load('sheets__team__id'))
        member.name = item.get_field_value(load('sheets__team__name'))
        member.status = item.get_field_value(load('sheets__team__status'))
        member.curator = item.get_field_value(load('sheets__team__curator'))
        member.manager = item.get_field_value(load('sheets__team__manager'))
        member.telegram = item.get_field_value(load('sheets__team__telegram'))
        member.trello = item.get_field_value(load('sheets__team__trello'))
        return member


def _get_str_data_item(data: dict, item_name: str) -> str:
    """Preprocess string data item from sheets"""
    return data[item_name].strip() if data.get(item_name) else ''


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    is_curator = Column(Boolean, default=False)

    def __repr__(self):
        return f'Chat {self.id} name={self.title}, curator={self.is_curator}'


class Reminder(Base):
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True)
    group_chat_id = Column(Integer, ForeignKey('chats.id'))
    creator_chat_id = Column(Integer)
    name = Column(String)  # short reminder name
    text = Column(String)  # full reminder text
    weekday = Column(Integer)   # e.g. monday is 0
    time = Column(String)  # e.g. "15:00"
    next_reminder_datetime = Column(DateTime)  # Moscow timezone
    frequency_days = Column(Integer)
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f'Reminder {self.name} group_chat_id={self.group_chat_id}'


class TrelloAnalytics(Base):
    __tablename__ = 'trello_analytics'
    # SQLite does not have datetime objects. Date format: '%Y-%m-%d'
    date = Column(String, primary_key=True)
    topic_suggestion = Column(Integer)
    topic_ready = Column(Integer)
    in_progress = Column(Integer)
    expect_this_week = Column(Integer)
    editors_check = Column(Integer)
    deadline_missed = Column(Integer)
    waiting_for_editors = Column(Integer)
    ready_to_issue = Column(Integer)


class Rubric(Base):
    __tablename__ = 'rubrics'
    name = Column(String, primary_key=True)
    vk_tag = Column(String)
    tg_tag = Column(String)

    @classmethod
    def from_dict(cls, data):
        rubric = cls()
        try:
            rubric.name = _get_field_or_throw(data['name'])
            rubric.vk_tag = _get_field_or_throw(data['vk_tag'])
            rubric.tg_tag = _get_field_or_throw(data['tg_tag'])
        except ValueError:
            return None
        return rubric

    def to_dict(self):
        return {
            'name': self.name,
            'vk_tag': self.vk_tag,
            'tg_tag': self.tg_tag,
        }

    @classmethod
    def from_sheetfu_item(cls, item):
        rubric = cls()
        try:
            rubric.name = item.get_field_value(load('sheets__rubric_name'))
            rubric.vk_tag = item.get_field_value(load('sheets__vk_tag'))
            rubric.tg_tag = item.get_field_value(load('sheets__tg_tag'))
        except ValueError:
            return None
        return rubric


def _get_field_or_throw(field):
    if field is None:
        raise ValueError
    return field
