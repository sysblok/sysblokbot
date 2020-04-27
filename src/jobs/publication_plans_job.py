import datetime
import logging
import time
from typing import Callable, List

from ..app_context import AppContext
from ..trello.trello_client import TrelloClient
from .utils import pretty_send


logger = logging.getLogger(__name__)


def execute(app_context: AppContext, send: Callable[[str], None]):
    # TODO: make it a decorator
    logger.info('Starting publication_plans_job...')

    paragraphs = []  # list of paragraph strings
    paragraphs.append('Всем привет!')

    paragraphs += _retrieve_cards_for_paragraph(
        trello_client=app_context.trello_client,
        title='Публикуем на неделе',
        list_ids=(
            app_context.lists_config['proofreading'],
            app_context.lists_config['done']
        ),
        custom_fields_config=app_context.custom_fields_config,
        show_due=True,
    )

    paragraphs += _retrieve_cards_for_paragraph(
        trello_client=app_context.trello_client,
        title='На редактуре',
        list_ids=(
            app_context.lists_config['edited_next_week']
        ),
        custom_fields_config=app_context.custom_fields_config,
        show_due=False,
    )

    pretty_send(paragraphs, send)
    logger.info('Finished publication_plans_job')


def _retrieve_cards_for_paragraph(
        trello_client: TrelloClient,
        title: str,
        list_ids: List[str],
        custom_fields_config: dict,
        show_due=True,
) -> List[str]:
    '''
    Returns a list of paragraphs that should always go in a single message.
    '''
    logger.info(f'Started counting: "{title}"')
    cards = trello_client.get_cards(list_ids)
    if show_due:
        cards.sort(key=lambda card: card.due)
    parse_failure_counter = 0

    paragraphs = [f'<b>{title}: {len(cards)}</b>']

    for card in cards:
        if not card:
            parse_failure_counter += 1
            continue
        card_fields = trello_client.get_card_custom_fields(card.id)
        authors = [
            field.value for field in card_fields
            if field.type_id == custom_fields_config['author']
        ]
        editors = [
            field.value for field in card_fields
            if field.type_id == custom_fields_config['editor']
        ]
        illustrators = [
            field.value for field in card_fields
            if field.type_id == custom_fields_config['illustrator']
        ]
        paragraphs.append(
            _format_card(
                card, authors, editors, illustrators, show_due=show_due
            )
        )

    if parse_failure_counter > 0:
        logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
    return paragraphs


def _format_card(
        card, authors, editors, illustrators, show_due=True
) -> str:
    # Name and url always present.
    card_text = f'<a href="{card.url}">{card.name}</a>\n'

    card_text += f'Авторы: {",".join(authors)} '
    card_text += f'Редакторы: {",".join(editors)} '
    card_text += f'Иллюстраторы: {",".join(illustrators)} '

    if show_due:
        card_text = f'<b>{card.due.strftime("%d.%m")}</b> — {card_text}'
    return card_text.strip()
