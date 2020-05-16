import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from .base_job import BaseJob
from ..consts import TrelloListAlias, TrelloCustomFieldTypeAlias, TrelloCardColor
from ..trello.trello_client import TrelloClient
from .utils import pretty_send

logger = logging.getLogger(__name__)


class PublicationPlansJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        paragraphs = []  # list of paragraph strings
        errors = {}
        paragraphs.append('Всем привет!')

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title='Публикуем на неделе',
            list_aliases=(TrelloListAlias.PROOFREADING, TrelloListAlias.DONE),
            errors=errors,
            show_due=True,
        )

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title='На редактуре',
            list_aliases=(TrelloListAlias.EDITED_NEXT_WEEK, ),
            errors=errors,
            show_due=False,
            need_illustrators=False,
        )

        paragraphs.append('Спасибо авторам, редакторам, кураторам и иллюстраторам! 🤖❤️')

        if len(errors) > 0:
            paragraphs = PublicationPlansJob._format_errors(errors)

        pretty_send(paragraphs, send)

    @staticmethod
    def _retrieve_cards_for_paragraph(
            trello_client: TrelloClient,
            title: str,
            list_aliases: List[TrelloListAlias],
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

        paragraphs = [f'<b>{title}: {len(cards)}</b>']

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

            paragraphs.append(
                PublicationPlansJob._format_card(
                    card, title, google_doc, authors, editors, illustrators, show_due=show_due
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs

    @staticmethod
    def _format_card(
            card, title, google_doc, authors, editors, illustrators, show_due=True
    ) -> str:
        # Name and google_doc url always present.
        card_text = f'<a href="{google_doc}">{title or card.name}</a>\n'

        card_text += f'Автор{"ы" if len(authors) > 1 else ""}: {", ".join(authors)}. '
        card_text += f'Редактор{"ы" if len(editors) > 1 else ""}: {", ".join(editors)}. '
        if len(illustrators) > 0:
            card_text += (
                f'Иллюстратор{"ы" if len(illustrators) > 1 else ""}: {", ".join(illustrators)}. '
            )

        if show_due:
            card_text = (
                f'<b>{card.due.strftime("%d.%m (%a)").lower()}</b> — {card_text}'
            )
        return card_text.strip()

    @staticmethod
    def _format_errors(errors: dict):
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
