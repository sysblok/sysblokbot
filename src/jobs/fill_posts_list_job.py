import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from .base_job import BaseJob
from ..consts import TrelloListAlias, TrelloCustomFieldTypeAlias, TrelloCardColor
from ..trello.trello_client import TrelloClient
from .utils import format_errors, pretty_send
from ..sheets.sheets_objects import RegistryPost

logger = logging.getLogger(__name__)


class FillPostsListJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        errors = {}
        registry_posts = []

        registry_posts += FillPostsListJob._retrieve_cards_for_registry(
            trello_client=app_context.trello_client,
            title='Публикуем на неделе',
            list_aliases=(TrelloListAlias.PROOFREADING, TrelloListAlias.DONE),
            errors=errors,
            show_due=True,
        )

        if len(errors) == 0:
            posts_added = app_context.sheets_client.update_posts_registry(registry_posts)
            if len(posts_added) == 0:
                paragraphs = [
                    'Информация о публикуемых на следующей неделе постах уже внесена в реестр. '
                    'Внести необходимые изменения можно в таблице “Реестр постов”.'
                ]
            else:
                paragraphs = ['<b>Добавлено в реестр постов:</b>'] + [
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
            title: str,
            list_aliases: List[str],
            errors: dict,
            show_due=True,
            need_illustrators=True,
    ) -> List[str]:
        '''
        Returns a list of paragraphs that should always go in a single message.
        '''
        logger.info(f'Started counting: "{title}"')
        list_ids = [trello_client.lists_config[alias] for alias in list_aliases]
        cards = trello_client.get_cards(list_ids)
        if show_due:
            cards.sort(key=lambda card: card.due or datetime.datetime.min)
        parse_failure_counter = 0

        registry_posts = []

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields_dict = trello_client.get_card_custom_fields_dict(card.id)
            authors = (
                card_fields_dict[TrelloCustomFieldTypeAlias.AUTHOR].value.split(',')
                if TrelloCustomFieldTypeAlias.AUTHOR in card_fields_dict else []
            )
            editors = (
                card_fields_dict[TrelloCustomFieldTypeAlias.EDITOR].value.split(',')
                if TrelloCustomFieldTypeAlias.EDITOR in card_fields_dict else []
            )
            illustrators = (
                card_fields_dict[TrelloCustomFieldTypeAlias.ILLUSTRATOR].value.split(',')
                if TrelloCustomFieldTypeAlias.ILLUSTRATOR in card_fields_dict else []
            )
            google_doc = card_fields_dict.get(TrelloCustomFieldTypeAlias.GOOGLE_DOC, None)
            title = card_fields_dict.get(TrelloCustomFieldTypeAlias.TITLE, None)

            label_names = [
                label.name for label in card.labels if label.color != TrelloCardColor.BLACK
            ]

            this_card_bad_fields = []
            if (
                    title is None and
                    card.lst.id != trello_client.lists_config[TrelloListAlias.EDITED_NEXT_WEEK]
            ):
                this_card_bad_fields.append('название поста')
            if google_doc is None:
                this_card_bad_fields.append('google doc')
            if len(authors) == 0:
                this_card_bad_fields.append('автор')
            if len(editors) == 0:  # unsure if need this -- and 'Архив' not in label_names:
                this_card_bad_fields.append('редактор')
            if len(illustrators) == 0 and need_illustrators and 'Архив' not in label_names:
                this_card_bad_fields.append('иллюстратор')
            if card.due is None and show_due:
                this_card_bad_fields.append('дата публикации')
            if len(label_names) == 0:
                this_card_bad_fields.append('рубрика')

            if len(this_card_bad_fields) > 0:
                logger.info(
                    f'Trello card is unsuitable for publication: {card.url} {this_card_bad_fields}'
                )
                errors[card] = this_card_bad_fields
                continue

            is_main_post = 'Главный пост' in [label.name for label in card.labels]
            is_archive_post = 'Архив' in [label.name for label in card.labels]

            registry_posts.append(
                RegistryPost(
                    card,
                    title.value,
                    ','.join(authors),
                    google_doc.value,
                    ','.join(editors),
                    ','.join(illustrators),
                    is_main_post,
                    is_archive_post,
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return registry_posts
