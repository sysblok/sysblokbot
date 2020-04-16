"""
A module for business logic-containing regular jobs.
Jobs should use corresponding client objects to interact with
Trello, Spreadsheets or Telegram API.
Jobs can be ran from scheduler or from anywhere else for a one-off action.
"""

import logging

from ..trello.trello_client import TrelloClient
from ..tg.sender import TelegramSender

logger = logging.getLogger(__name__)


def sample_job(trello_client, sheets_client, telegram_sender):
    # Logic here could include retrieving data from trello/sheets
    # and sending a notification to corresponding user.
    print("I am a job and I'm done")


def manager_stats_job(
        trello_client: TrelloClient,
        telegram_sender: TelegramSender,
        lists_config: dict
):
    # TODO: make it a decorator
    logger.info('Starting manager_stats_job...')
    '''
3. Карточки без тега рубрики в списке “Уже пишу” и следующих списках 
(название карточки, название списка в Трелло, ссылка на карточку в Trello + юзернеймы в Telegram куратора и автора (после интеграции с GS))

4. Авторы без карточек
(юзернейм в Trello (без интеграции с GS) / название рубрики, юзернейм в Telegram (после интеграции с GS))

5. Карточки с просроченным дедлайном 
(дата, название карточки, название рубрики, ссылка на карточку в Trello + юзернеймы в Telegram куратора и автора (после интеграции с GS))
    '''
    cards_no_author = list(filter(
        lambda card: not card.members,
        trello_client.get_cards(
            (
                lists_config['in_progress'],
                lists_config['editor'],
                lists_config['edited_next_week'],
                lists_config['edited_sometimes'],
                lists_config['chief_editor'],
                lists_config['proofreading'],
                lists_config['done'],
            )
        )
    ))
    parse_failure_counter = 0
    cards_no_author_text = f'<b>Не указан автор в карточке: {len(cards_no_author)}</b>'
    for card in cards_no_author:
        if not card:
            parse_failure_counter += 1
        cards_no_author_text += f'\n\n{_format_card(card, due=False, members=False)}'
    telegram_sender.send_to_manager(cards_no_author_text[:4096])

    if parse_failure_counter > 0:
        telegram_sender.send_to_manager(
            f'Ошибок парсинга карточек: {parse_failure_counter}!'
        )

    cards_no_due_in_progress = list(filter(
        lambda card: not card.due,
        trello_client.get_cards(lists_config['in_progress'])
    ))
    
    logger.info('Finished manager_stats_job')


def _format_card(card, due=True, members=True):
    card_text = f'<a href="{card.url}">{card.name}</a>'
    # If no labels assigned, don't render them to text.
    if card.labels:
        card_text = f'{card_text}, {card.labels}'
    
    # Avoiding message overflow, strip explanations in ()
    list_name = card.list_name[:card.list_name.find('(')].strip()
    card_text += f', колонка "{list_name}"'

    if due:
        card_text = f'<b>{card.due}</b> - {card_text}'
    if members:
        card_text += f'\nУчастники: {card.members}'
    return card_text
