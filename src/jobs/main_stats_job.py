import datetime
import logging
from typing import Callable, List, Tuple

from .base_job import BaseJob
from . import utils
from ..app_context import AppContext
from ..consts import TrelloListAlias
from ..strings import load

logger = logging.getLogger(__name__)


class TrelloAnalyticsJob(BaseJob):
    new_statistic = {}

    @staticmethod
    def _execute(app_context: AppContext,
                 send: Callable[[str], None],
                 called_from_handler: bool = False):
        paragraphs = [load('main_stats_job__intro')]

        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('main_stats_job__title_pending_approval'),
            list_aliases=(
                TrelloListAlias.TOPIC_SUGGESTION,
            ),
            column_name='topic_suggestion'
        )
        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('main_stats_job__title_author_search'),
            list_aliases=(
                TrelloListAlias.TOPIC_READY,
            ),
            column_name='topic_ready'
        )

        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('main_stats_job__title_in_work'),
            list_aliases=(
                TrelloListAlias.IN_PROGRESS,
            ),
            column_name='in_progress'
        )

        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('main_stats_job__title_expect_this_week'),
            list_aliases=(
                TrelloListAlias.IN_PROGRESS,
            ),
            filter_func=TrelloAnalyticsJob._card_deadline_is_next_week,
            column_name='expect_this_week'
        )

        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title=load('main_stats_job__title_editors_check'),
            list_aliases=(
                TrelloListAlias.TO_EDITOR,
                TrelloListAlias.EDITED_NEXT_WEEK,
                TrelloListAlias.EDITED_SOMETIMES,
                TrelloListAlias.TO_CHIEF_EDITOR,
            ),
            column_name='editors_check'
        )
        if not called_from_handler:
            TrelloAnalyticsJob.add_new_statistics(app_context, TrelloAnalyticsJob.new_statistic)

        utils.pretty_send(paragraphs, send)

    @staticmethod
    def _card_deadline_is_next_week(card) -> bool:
        # should count from last called date, currently correct only for scheduled calls
        if card.due is None:
            return False
        timedelta = card.due - datetime.datetime.now()
        return 0 <= timedelta.days <= 7

    @staticmethod
    def _retrieve_cards_for_paragraph(
            app_context: AppContext,
            title: str,
            list_aliases: Tuple[str],
            column_name: str,
            filter_func=None,
    ) -> List[str]:
        '''
        Returns a list of paragraphs that should always go in a single message.
        '''
        logger.info(f'Started counting: "{title}"')
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        cards = list(filter(filter_func, app_context.trello_client.get_cards(list_ids)))
        statistics = utils.retrieve_last_trello_analytics(app_context.db_client)
        TrelloAnalyticsJob.new_statistic[column_name] = len(cards)

        paragraph = load(
            'common_report__list_title_and_size',
            title=title,
            length=len(cards)
        )
        if statistics:
            delta = len(cards) - int(statistics[column_name])
            if delta != 0:
                delta_string = load(
                    'main_stats_job__delta_week',
                    sign='+' if delta > 0 else '-',
                    delta=abs(delta)
                )
                paragraph = f'{paragraph} {delta_string}'
        return [paragraph]

    @staticmethod
    def add_new_statistics(app_context, data):
        data['date'] = str(datetime.date.today())
        utils.add_statistic(app_context.db_client, data)
