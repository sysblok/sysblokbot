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
    errors = {}
    paragraphs.append('Всем привет!')

    paragraphs += _retrieve_cards_for_paragraph(
        trello_client=app_context.trello_client,
        title='Публикуем на неделе',
        list_ids=(
            app_context.lists_config['proofreading'],
            app_context.lists_config['done']
        ),
        custom_fields_config=app_context.custom_fields_config,
        errors=errors,
        show_due=True,
    )

    paragraphs += _retrieve_cards_for_paragraph(
        trello_client=app_context.trello_client,
        title='На редактуре',
        list_ids=(
            app_context.lists_config['edited_next_week']
        ),
        custom_fields_config=app_context.custom_fields_config,
        errors=errors,
        show_due=False,
        need_illustrators=False,
    )

    if len(errors) > 0:
        paragraphs = _format_errors(errors)

    pretty_send(paragraphs, send)
    logger.info('Finished publication_plans_job')


def _retrieve_cards_for_paragraph(
        trello_client: TrelloClient,
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
    cards = trello_client.get_cards(list_ids)
    if show_due:
        cards.sort(key=lambda card: card.due)
    parse_failure_counter = 0

    paragraphs = [f'<b>{title}: {len(cards)}</b>']

    for card in cards:
        if not card:
            parse_failure_counter += 1
            continue

        card_fields_dict = trello_client.get_card_custom_fields_dict(card.id)
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

        this_card_bad_fields = []
        if title is None:
            this_card_bad_fields.append('название поста')
        if google_doc is None:
            this_card_bad_fields.append('google doc')
        if len(authors) == 0:
            this_card_bad_fields.append('автор')
        if len(editors) == 0:
            this_card_bad_fields.append('редактор')
        if len(illustrators) == 0 and need_illustrators:
            this_card_bad_fields.append('иллюстратор')
        if card.due is None and show_due:
            this_card_bad_fields.append('дата публикации')

        if len(this_card_bad_fields) > 0:
            logger.error(f'Trello card is unsuitable for publication: {card.url}')
            errors[card] = this_card_bad_fields
            continue

        paragraphs.append(
            _format_card(
                card, google_doc, authors, editors, illustrators, show_due=show_due
            )
        )

    if parse_failure_counter > 0:
        logger.error(f'Unparsed cards encountered: {parse_failure_counter}')
    return paragraphs


def _format_card(
        card, google_doc, authors, editors, illustrators, show_due=True
) -> str:
    # Name and google_doc url always present.
    card_text = f'<a href="{google_doc}">{card.name}</a>\n'

    card_text += f'Автор{"ы" if len(authors) > 1 else ""}: \
{", ".join(authors)}. '
    card_text += f'Редактор{"ы" if len(editors) > 1 else ""}: \
{", ".join(editors)}. '
    card_text += f'Иллюстратор{"ы" if len(illustrators) > 1 else ""}: \
{", ".join(illustrators)}. '

    if show_due:
        card_text = f'<b>{card.due.strftime("%d.%m")}</b> — {card_text}'
    return card_text.strip()


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
