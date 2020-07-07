import datetime
import logging
from typing import Callable, List, Tuple

from .base_job import BaseJob
from . import utils
from ..app_context import AppContext
from ..consts import TrelloListAlias

logger = logging.getLogger(__name__)


class TrelloAnalyticsJob(BaseJob):
    new_statistic = {}

    @staticmethod
    def _execute(app_context: AppContext,
                 send: Callable[[str], None],
                 called_from_handler: bool = False):
        paragraphs = []
        paragraphs.append(
            'Всем привет! Еженедельная статистика работы редакции:\n#сб_stats'
        )

        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title='Темы в ожидании одобрения',
            list_aliases=(
                TrelloListAlias.TOPIC_SUGGESTION,
            ),
            column_name='topic_suggestion'
        )
        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title='В поиске автора',
            list_aliases=(
                TrelloListAlias.TOPIC_READY,
            ),
            column_name='topic_ready'
        )

        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title='В работе у авторов',
            list_aliases=(
                TrelloListAlias.IN_PROGRESS,
            ),
            column_name='in_progress'
        )

        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title='Ожидает готовности на неделе',
            list_aliases=(
                TrelloListAlias.IN_PROGRESS,
            ),
            filter_func=TrelloAnalyticsJob._is_card_deadline,
            column_name='expect_this_week'
        )

        paragraphs += TrelloAnalyticsJob._retrieve_cards_for_paragraph(
            app_context=app_context,
            title='В работе у редакторов',
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
    def _is_card_deadline(card) -> bool:
        return card.due is not None

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
        list_ids = [app_context.trello_client.lists_config[alias] for alias in list_aliases]
        cards = list(filter(filter_func, app_context.trello_client.get_cards(list_ids)))
        statistics = TrelloAnalyticsJob._get_last_statistic(app_context)
        TrelloAnalyticsJob.new_statistic[column_name] = len(cards)
        if statistics:
            delta = len(cards) - int(statistics[column_name])
            paragraphs = [f'{title}: {len(cards)}'
                          f'<b>({"+" if delta > 0 else ""}{delta} за неделю)</b>']
            return paragraphs
        else:
            return [f'{title}: {len(cards)}']

    @staticmethod
    def _get_last_statistic(app_context):
        statistic_data = utils.retrieve_statistc(app_context.db_client)  # last week's statistics
        if statistic_data:
            last_weeks_statistics = statistic_data[-1]
            return last_weeks_statistics

    @staticmethod
    def add_new_statistics(app_context, data):
        data['date'] = str(datetime.date.today())
        utils.add_statistic(app_context.db_client, data)
