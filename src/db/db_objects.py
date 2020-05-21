from sqlalchemy import Column, Integer, String
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
        author.name = data['name']
        author.curator = data['curator']
        author.status = data['status']
        author.telegram = data['telegram']
        author.trello = data['trello']
        return author
