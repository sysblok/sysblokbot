import datetime
import logging
from typing import Callable, Tuple
import matplotlib as mpl
import numpy as np
import matplotlib.pyplot as plt
from .base_job import BaseJob
from . import utils
from ..app_context import AppContext
from ..consts import TrelloListAlias
from ..db.db_objects import TrelloAnalytics
from ..strings import load
from ..utils import card_checks

logger = logging.getLogger(__name__)
mpl.use('Agg')

DEFAULT_BAR_HEIGHT = 0.4


class EditorialBoardVisualStatsJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext,
                 send: Callable[[str], None],
                 called_from_handler: bool = False):
        new_analytics = TrelloAnalytics()
        # the order here is displayed reversed as the chart is build from the bottom up :)
        stats = [
            EditorialBoardVisualStatsJob._make_dict_for_category(
                app_context=app_context,
                title=load('editorial_board_stats_job__title_ready_to_issue'),
                list_aliases=(
                    TrelloListAlias.EDITED_SOMETIMES,
                    TrelloListAlias.TO_CHIEF_EDITOR,
                    TrelloListAlias.PROOFREADING,
                    TrelloListAlias.DONE,
                ),
                column_name='ready_to_issue'
            ),
            EditorialBoardVisualStatsJob._make_dict_for_category(
                app_context=app_context,
                title=load('editorial_board_stats_job__title_editors_check'),
                list_aliases=(
                    TrelloListAlias.TO_SEO_EDITOR,
                    TrelloListAlias.EDITED_NEXT_WEEK,
                ),
                column_name='editors_check'
            ),
            EditorialBoardVisualStatsJob._make_dict_for_category(
                app_context=app_context,
                title=load('editorial_board_stats_job__title_waiting_for_editors'),
                list_aliases=(
                    TrelloListAlias.TO_EDITOR,
                ),
                column_name='waiting_for_editors',
            ),
            EditorialBoardVisualStatsJob._make_dict_for_category(
                app_context=app_context,
                title=load('editorial_board_stats_job__title_expect_this_week'),
                list_aliases=(
                    TrelloListAlias.IN_PROGRESS,
                ),
                filter_func=(
                    lambda card: EditorialBoardVisualStatsJob._card_deadline_is_next_week(
                        card, app_context
                    )
                ),
                column_name='expect_this_week'
            ),
            EditorialBoardVisualStatsJob._make_dict_for_category(
                app_context=app_context,
                title=load('editorial_board_stats_job__title_deadline_missed'),
                list_aliases=(
                    TrelloListAlias.IN_PROGRESS,
                ),
                column_name='deadline_missed',
                filter_func=lambda card: card_checks.is_deadline_missed(card, app_context)[0]
            ),
            EditorialBoardVisualStatsJob._make_dict_for_category(
                app_context=app_context,
                title=load('editorial_board_stats_job__title_in_work'),
                list_aliases=(
                    TrelloListAlias.IN_PROGRESS,
                ),
                column_name='in_progress'
            ),
            EditorialBoardVisualStatsJob._make_dict_for_category(
                app_context=app_context,
                title=load('editorial_board_stats_job__title_author_search'),
                list_aliases=(
                    TrelloListAlias.TOPIC_READY,
                ),
                column_name='topic_ready'
            ),
            EditorialBoardVisualStatsJob._make_dict_for_category(
                app_context=app_context,
                title=load('editorial_board_stats_job__title_pending_approval'),
                list_aliases=(
                    TrelloListAlias.TOPIC_SUGGESTION,
                ),
                column_name='topic_suggestion'
            ),
        ]

        date_interval = ''
        try:
            last_stats_date = utils.retrieve_last_trello_analytics_date(app_context.db_client)
            if last_stats_date is None:
                date_interval = ''
                logger.warning(f'Last stats date is null. Setting the date interval to zero')
            else:
                today = datetime.datetime.today()
                date_interval = f'{last_stats_date.strftime("%d.%m")}-{today.strftime("%d.%m")}'
        except Exception as e:
            logger.error(f'Could not get main stats date interval: {e}')

        if not called_from_handler:
            # scheduled runs should write results to db, otherwise not
            today_db_str = datetime.datetime.today().strftime('%Y-%m-%d')
            new_analytics.date = today_db_str
            app_context.db_client.add_item_to_statistics_table(new_analytics)

        fig, ax = plt.subplots()
        labels = [x['title'] for x in stats]
        x = np.arange(len(labels))
        plt.xticks(rotation=90)
        # Note we add the `width` parameter now which sets the width of each bar.
        last_week = [x['previous_period'] for x in stats]
        ax.barh(
            x,
            last_week,
            height=DEFAULT_BAR_HEIGHT,
            label='Предыдущая неделя'
        )
        # Same thing, but for the current week
        actual_week = [x['current_period'] for x in stats]
        ax.barh(
            x + DEFAULT_BAR_HEIGHT,
            actual_week,
            height=DEFAULT_BAR_HEIGHT,
            label='Текущая неделя'
        )
        ax.set_xlabel('Count')
        ax.set_title('Visual Stats Board')
        ax.set_yticks(x, labels)
        # reverse the legend
        handles, labels = ax.get_legend_handles_labels()
        ax.legend(reversed(handles), reversed(labels))

        plt.savefig('foo.png', bbox_inches='tight')
        send('foo.png')

    @staticmethod
    def _card_deadline_is_next_week(card, app_context) -> bool:
        if card.due is None:
            return False
        last_analytics_date = (
            utils.retrieve_last_trello_analytics_date(app_context.db_client)
            or datetime.datetime.now()  # in case database is empty, e.g. local testing
        )
        timedelta = card.due - last_analytics_date
        return 0 <= timedelta.days < 7

    @staticmethod
    def _make_dict_for_category(
            app_context: AppContext,
            title: str,
            list_aliases: Tuple,
            column_name: str,
            filter_func=None,
    ) -> dict:
        """
        Returns a dict for category statistics (e.g. {"title": "В работе у авторов",
                                                        "previous_period": 11,
                                                        "current_period": 13})
        """
        logger.info(f'Started counting: "{title}"')
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        cards = list(filter(filter_func, app_context.trello_client.get_cards(list_ids)))
        statistics = utils.retrieve_last_trello_analytics(app_context.db_client)
        previous_data = 0
        if statistics:  # otherwise it's a first command run
            previous_data = int(getattr(statistics, column_name))
        return {'title': title, 'previous_period': previous_data, 'current_period': len(cards)}
