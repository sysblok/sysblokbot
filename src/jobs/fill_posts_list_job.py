import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from ..consts import TrelloListAlias, TrelloCardColor
from ..sheets.sheets_objects import RegistryPost
from ..strings import load
from ..trello.trello_client import TrelloClient
from .base_job import BaseJob
from .utils import format_errors, pretty_send

logger = logging.getLogger(__name__)


class FillPostsListJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        errors = {}
        registry_posts = []

        registry_posts += FillPostsListJob._retrieve_cards_for_registry(
            trello_client=app_context.trello_client,
            list_aliases=(TrelloListAlias.PROOFREADING, TrelloListAlias.DONE),
            errors=errors,
            show_due=True,
            strict_archive_rules=True,
        )

        if len(errors) == 0:
            posts_added = app_context.sheets_client.update_posts_registry(registry_posts)
            if len(posts_added) == 0:
                paragraphs = [load('fill_posts_list_job_unchanged')]
            else:
                paragraphs = [load('fill_posts_list_job_success')] + [
                    '\n'.join(
                        f'{index + 1}) {post_name}' for index, post_name in enumerate(posts_added)
                    )
                ]
        else:
            paragraphs = format_errors(errors)

        pretty_send(paragraphs, send)

    @staticmethod
    def _retrieve_cards_for_registry(
            trello_client: TrelloClient,
            list_aliases: List[str],
            errors: dict,
            show_due=True,
            need_illustrators=True,
            strict_archive_rules=True,
    ) -> List[str]:
        '''
        Returns a list of paragraphs that should always go in a single message.
        '''
        list_ids = trello_client.get_list_id_from_aliases(list_aliases)
        cards = trello_client.get_cards(list_ids)
        if show_due:
            cards.sort(key=lambda card: card.due or datetime.datetime.min)
        parse_failure_counter = 0

        registry_posts = []

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = trello_client.get_custom_fields(card.id)

            label_names = [
                label.name for label in card.labels if label.color != TrelloCardColor.BLACK
            ]

            is_main_post = 'Главный пост' in [label.name for label in card.labels]
            is_archive_post = 'Архив' in [label.name for label in card.labels]

            this_card_bad_fields = []
            if (
                    card_fields.title is None and
                    card.lst.id != trello_client.lists_config[TrelloListAlias.EDITED_NEXT_WEEK]
            ):
                this_card_bad_fields.append('название поста')
            if card_fields.google_doc is None:
                this_card_bad_fields.append('google doc')
            if len(card_fields.authors) == 0:
                this_card_bad_fields.append('автор')
            if len(card_fields.editors) == 0:  # and 'Архив' not in label_names:
                this_card_bad_fields.append('редактор')
            if card_fields.cover is None and not is_archive_post:
                this_card_bad_fields.append('обложка')
            if (
                    len(card_fields.illustrators) == 0 and need_illustrators and
                    not is_archive_post
            ):
                this_card_bad_fields.append('иллюстратор')
            if card.due is None and show_due:
                this_card_bad_fields.append('дата публикации')
            if len(label_names) == 0:
                this_card_bad_fields.append('рубрика')

            if (
                    len(this_card_bad_fields) > 0
                    and not (is_archive_post and not strict_archive_rules)
            ):
                logger.info(
                    f'Trello card is unsuitable for publication: {card.url} {this_card_bad_fields}'
                )
                errors[card] = this_card_bad_fields
                continue

            registry_posts.append(
                RegistryPost(
                    card,
                    card_fields,
                    is_main_post,
                    is_archive_post,
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return registry_posts
