import logging

from ..consts import TrelloCardColor
from ..trello.trello_objects import CardCustomFields, TrelloCard


logger = logging.getLogger(__name__)


class RegistryPost:
    def __init__(
            self,
            card: TrelloCard,
            custom_fields: CardCustomFields,
            is_main_post: bool,
            is_archive_post: bool,
    ):
        self.title = custom_fields.title
        self.authors = ','.join(custom_fields.authors)
        self.trello_url = card.url
        # We filter BLACK cards as this is an auxiliary label
        self.rubrics = [
            label.name for label in card.labels
            if label.color != TrelloCardColor.BLACK
        ]
        self.google_doc = custom_fields.google_doc
        self.editors = ','.join(custom_fields.editors)
        self.illustrators = ','.join(custom_fields.illustrators)
        self.is_main_post = is_main_post
        self.is_archive_post = is_archive_post
