import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from .base_job import BaseJob
from ..trello.trello_client import TrelloClient
from .utils import pretty_send
from ..sheets.sheets_objects import RegistryPost

logger = logging.getLogger(__name__)


class FillPostsListJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        errors = {}
        registry_posts = []

        registry_posts += FillPostsListJob._retrieve_cards_for_registry(
            app_context=app_context,
            title='Публикуем на неделе',
            list_ids=(
                app_context.lists_config['proofreading'],
                app_context.lists_config['done']
            ),
            custom_fields_config=app_context.custom_fields_config,
            errors=errors,
            show_due=True,
        )

        posts_added, before, after = \
            app_context.sheets_client.update_posts_registry(registry_posts)

        assert before + posts_added == after

        if len(errors) > 0:
            paragraphs = FillPostsListJob._format_errors(errors)
        elif posts_added == 0:
            paragraphs = [
                '''Информация о публикуемых на следующей неделе постах уже внесена в реестр. 
Внести необходимые изменения можно в таблице “Реестр постов”.'''
            ]
        else:
            paragraphs = [f'Экспортировано {posts_added} постов']

        pretty_send(paragraphs, send)

    @staticmethod
    def _retrieve_cards_for_registry(
            app_context: AppContext,
            title: str,
            list_ids: List[str],
            custom_fields_config: dict,
            errors: dict,
            show_due=True,
            need_illustrators=True,
    ) -> List[str]:
        '''
        Returns a list of paragraphs that should always go in a single message.
        '''
        logger.info(f'Started counting: "{title}"')
        cards = app_context.trello_client.get_cards(list_ids)
        if show_due:
            cards.sort(key=lambda card: card.due)
        parse_failure_counter = 0

        registry_posts = []

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields_dict = app_context.trello_client.get_card_custom_fields_dict(card.id)
            authors = \
                card_fields_dict[custom_fields_config['author']].value.split(',') \
                if custom_fields_config['author'] in card_fields_dict else []
            editors = \
                card_fields_dict[custom_fields_config['editor']].value.split(',') \
                if custom_fields_config['editor'] in card_fields_dict else []
            illustrators = \
                card_fields_dict[custom_fields_config['illustrator']].value.split(',') \
                if custom_fields_config['illustrator'] in card_fields_dict else []
            google_doc = card_fields_dict.get(custom_fields_config['google_doc'], None)
            title = card_fields_dict.get(custom_fields_config['title'], None)

            label_names = [label.name for label in card.labels]

            this_card_bad_fields = []
            if title is None and card.lst.id != app_context.lists_config['edited_next_week']:
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
            if len(card.labels) == 0:
                this_card_bad_fields.append('рубрика')

            if len(this_card_bad_fields) > 0:
                logger.error(
                    f'Trello card is unsuitable for publication: {card.url} {this_card_bad_fields}'
                )
                errors[card] = this_card_bad_fields
                continue

            is_main_post = 'Главный пост' in label_names

            registry_posts.append(
                RegistryPost(card, title.value, ','.join(authors), google_doc.value,
                             ','.join(editors), ','.join(illustrators), is_main_post)
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return registry_posts

    @staticmethod
    def _format_errors(errors: dict):
        # copied from publication_plans_job.py
        # it will be merged there later, hopefully
        error_messages = []
        for bad_card, bad_fields in errors.items():
            card_error_message = f'В карточке <a href="{bad_card.url}">\
{bad_card.name}</a> не заполнено: {", ".join(bad_fields)}'
            error_messages.append(card_error_message)
        paragraphs = [
            'Не могу сгенерировать сводку.',
            '\n'.join(error_messages),
            'Пожалуйста, заполни требуемые поля в карточках \
    и запусти генерацию снова.'
        ]
        return paragraphs
