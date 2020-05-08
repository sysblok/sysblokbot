import logging

from ..consts import TrelloCardColor
from ..trello.trello_objects import TrelloCard


logger = logging.getLogger(__name__)


class RegistryPost:
    def __init__(
            self,
            card: TrelloCard,
            title: str,
            authors: str,
            google_doc: str,
            editors: str,
            illustrators: str,
            is_main_post: bool,
    ):
        self.title = title
        self.authors = authors
        self.trello_url = card.url
        # We filter BLACK cards as this is an auxiliary label
        self.rubrics = [
            label.name for label in card.labels
            if label.color != TrelloCardColor.BLACK
        ]
        self.google_doc = google_doc
        self.editors = editors
        self.illustrators = illustrators
        self.is_main_post = is_main_post
