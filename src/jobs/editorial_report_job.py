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


class EditorialReportJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None]):
        paragraphs = []  # list of paragraph strings
        errors = {}
        paragraphs.append('Всем привет! Еженедельный редакторский отчет. #cб_редчет')

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title='Отредактировано и ожидает финальной проверки',
            list_aliases=(TrelloListAlias.EDITED_SOMETIMES, TrelloListAlias.TO_CHIEF_EDITOR),
            errors=errors,
            need_title=True,
        )

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title='На доработке у автора',
            list_aliases=(TrelloListAlias.IN_PROGRESS, ),
            errors=errors,
            moved_from_exclusive=(TrelloListAlias.EDITED_NEXT_WEEK, )
        )

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title='На редактуре',
            list_aliases=(TrelloListAlias.EDITED_NEXT_WEEK, ),
            errors=errors,
        )

        paragraphs += EditorialReportJob._retrieve_cards_for_paragraph(
            trello_client=app_context.trello_client,
            title='Ожидает редактуры',
            list_aliases=(TrelloListAlias.TO_EDITOR, ),
            errors=errors,
            need_editor=False,
        )

        if len(errors) > 0:
            paragraphs = EditorialReportJob._format_errors(errors)

        pretty_send(paragraphs, send)

    @staticmethod
    def _card_is_urgent(card):
        return 'Срочно' in [label.name for label in card.labels]

    @staticmethod
    def _retrieve_cards_for_paragraph(
            trello_client: TrelloClient,
            title: str,
            list_aliases: List[TrelloListAlias],
            errors: dict,
            moved_from_exclusive: List[TrelloListAlias] = (),
            show_post_title=False,
            need_editor=True,
            need_title=False,
    ) -> List[str]:
        '''
        Returns a list of paragraphs that should always go in a single message.
        '''
        logger.info(f'Started counting: "{title}"')
        list_ids = [trello_client.lists_config[alias] for alias in list_aliases]
        list_moved_from_ids = [trello_client.lists_config[alias] for alias in moved_from_exclusive]
        cards = trello_client.get_cards(list_ids)
        parse_failure_counter = 0

        card_ids = [card.id for card in cards]
        cards_actions = trello_client.get_action_update_cards(card_ids)

        cards_filtered = []

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            actions_moved_here = sorted([
                action for action in cards_actions[card.id]
                if (
                    action.list_after_id == card.lst.id
                    and (
                        len(list_moved_from_ids) == 0
                        or action.list_before_id in list_moved_from_ids
                    )
                )
            ], key=lambda action: action.date, reverse=True)

            if len(actions_moved_here) == 0:
                if len(moved_from_exclusive) > 0:
                    # otherwise we don't really care where the card came from
                    continue
                logger.info(f'Card {card.url} unexpectedly appeared in list {card.lst.name}')
            else:
                card.due = actions_moved_here[0].date
            cards_filtered.append(card)

        paragraphs = [f'<b>{title}: {len(cards_filtered)}</b>']

        for card in sorted(
            cards_filtered,
            key=lambda card: (
                EditorialReportJob._card_is_urgent(card), card.due is not None, card.due
            ), reverse=True
        ):
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
            google_doc = card_fields_dict.get(TrelloCustomFieldTypeAlias.GOOGLE_DOC, None)
            title = card_fields_dict.get(TrelloCustomFieldTypeAlias.TITLE, None)

            this_card_bad_fields = []
            if title is None and need_title:
                this_card_bad_fields.append('название поста')
            if google_doc is None:
                this_card_bad_fields.append('google doc')
            if len(authors) == 0:
                this_card_bad_fields.append('автор')
            if len(editors) == 0 and need_editor:
                this_card_bad_fields.append('редактор')

            if len(this_card_bad_fields) > 0:
                logger.info(
                    f'Trello card is unsuitable for publication: {card.url} {this_card_bad_fields}'
                )
                errors[card] = this_card_bad_fields
                continue

            paragraphs.append(
                EditorialReportJob._format_card(
                    card, title if need_title else card.name, google_doc,
                    authors, editors, is_urgent=EditorialReportJob._card_is_urgent(card)
                )
            )

        if parse_failure_counter > 0:
            logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
        return paragraphs

    @staticmethod
    def _format_card(
            card, title, google_doc, authors, editors, is_urgent=False
    ) -> str:
        # Name and google_doc url always present.
        card_text = f'<a href="{card.url}">{title or card.name}</a>\n'

        card_text += f'Автор{"ы" if len(authors) > 1 else ""}: {", ".join(authors)}. '
        if len(editors) > 0:
            card_text += f'Редактор{"ы" if len(editors) > 1 else ""}: {", ".join(editors)}. '

        if card.due:
            card_text = (
                f'<b>с {card.due.strftime("%d.%m (%a)").lower()} '
                f'{"(Срочно!)" if is_urgent else ""}</b> — {card_text}'
            )
        else:
            card_text = (
                f'<b>с ??.??</b> — {card_text}'
            )
        return card_text.strip()

    @staticmethod
    def _format_errors(errors: dict):
        error_messages = []
        for bad_card, bad_fields in errors.items():
            card_error_message = (
                f'В карточке <a href="{bad_card.url}">{bad_card.name}</a>'
                f' не заполнено: {", ".join(bad_fields)}'
            )
            error_messages.append(card_error_message)
        paragraphs = [
            'Не могу сгенерировать сводку.',
            '\n'.join(error_messages),
            'Пожалуйста, заполни требуемые поля в карточках и запусти генерацию снова.'
        ]
        return paragraphs
