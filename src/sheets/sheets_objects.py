import logging


logger = logging.getLogger(__name__)


class RegistryPost:
    def __init__(self, card, title, author, google_doc):
        self.title = title
        self.author = author
        self.trello_url = card.url
        self.rubrics = ','.join([label.name for label in card.labels])
        self.google_doc = google_doc
