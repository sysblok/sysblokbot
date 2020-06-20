from sqlalchemy import Column, Integer, String, ForeignKey, 
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


def _get_str_data_item(data: dict, item_name: str) -> str:
    """Preprocess string data item from sheets"""
    return data[item_name].strip() if data.get(item_name) else ''


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    name = Column(String)


class Reminder(Base):
    __tablename__ = 'reminders'

    id = Column(Integer, primary_key=True, sqlite_autoincrement=True)
    chat_id = Column(Integer, ForeignKey('chats.id'))
    name = Column(String)  # short reminder name
    text = Column(String)  # full reminder text
    weekday = Column(String)   # e.g. "wednesday"
    time = Column(String)  # e.g. "15:00"
    frequency = Column(String)  #

    def __repr__(self):
        return f'Reminder {self.name} chat_id={self.chat_id}'
