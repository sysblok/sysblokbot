"""
A module for business logic-containing regular jobs.
Jobs should use corresponding client objects to interact with
Trello, Spreadsheets or Telegram API.
Jobs can be ran from scheduler or from anywhere else for a one-off action.
"""

import logging

from ..bot import SysBlokBot

logger = logging.getLogger(__name__)


def sample_job(bot):
    # Logic here could include retrieving data from trello/sheets
    # and sending a notification to corresponding user.
    print("I am a job and I'm done")


def manager_stats_job(
        bot: SysBlokBot,
        lists_config: dict  # move that to db
):
    # TODO: make it a decorator
    logger.info('Starting manager_stats_job...')

    cards_no_author = list(filter(
        lambda card: not card.members,
        bot.trello_client.get_cards(
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
    bot.telegram_sender.send_to_manager(cards_no_author_text[:4096])

    if parse_failure_counter > 0:
        bot.telegram_sender.send_to_manager(
            f'Ошибок парсинга карточек: {parse_failure_counter}!'
        )

    cards_no_due_in_progress = list(filter(
        lambda card: not card.due,
        bot.trello_client.get_cards(lists_config['in_progress'])
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
