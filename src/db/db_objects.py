from sqlalchemy import Column, Integer, String, ForeignKey
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
        author.name = data['name'].strip()
        author.curator = data['curator'].strip()
        author.status = data['status'].strip()
        author.telegram = data['telegram'].strip()
        author.trello = data['trello'].strip()
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
        curator.name = data['name'].strip()
        curator.telegram = data['telegram'].strip()
        curator.team = data['team'].strip()
        curator.role = data['role'].strip()
        curator.section = data['section'].strip()
        curator.trello_labels = data['trello_labels'].strip()
        return curator
