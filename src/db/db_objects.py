from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base

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


class Curator(Base):
    __tablename__ = 'curators'

    name = Column(String, primary_key=True)
    telegram = Column(String)
    role = Column(String, ForeignKey('authors.curator'))  # e.g. "Куратор NLP 1"
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


def _get_str_data_item(data: dict, item_name: str) -> str:
    """Preprocess string data item from sheets"""
    return data[item_name].strip() if data.get(item_name) else ''


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    title = Column(String)


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

    def __repr__(self):
        return f'Reminder {self.name} group_chat_id={self.group_chat_id}'


class Statistic(Base):
    __tablename__ = 'statistic'
    date = Column(String, primary_key=True)
    topic_suggestion = Column(Integer)
    topic_ready = Column(Integer)
    in_progress = Column(Integer)
    expect_this_week = Column(Integer)
    editors_check = Column(Integer)

    @classmethod
    def from_dict(cls, data):
        statistic = cls()
        statistic.date = _get_str_data_item(data, 'date')
        statistic.topic_suggestion = _get_str_data_item(data, 'topic_suggestion')
        statistic.topic_ready = _get_str_data_item(data, 'topic_ready')
        statistic.in_progress = _get_str_data_item(data, 'in_progress')
        statistic.expect_this_week = _get_str_data_item(data, 'expect_this_week')
        statistic.editors_check = _get_str_data_item(data, 'editors_check')
        return statistic
