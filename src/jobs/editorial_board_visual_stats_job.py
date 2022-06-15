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

DEFAULT_BAR_WIDTH = 0.4


class EditorialBoardVisualStatsJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext,
                 send: Callable[[str], None],
                 called_from_handler: bool = False):
        new_analytics = TrelloAnalytics()
        stats = [
            EditorialBoardVisualStatsJob._make_text_for_category(
                app_context=app_context,
                new_analytics=new_analytics,
                title=load('editorial_board_stats_job__title_pending_approval'),
                list_aliases=(
                    TrelloListAlias.TOPIC_SUGGESTION,
                ),
                column_name='topic_suggestion'
            ),
            EditorialBoardVisualStatsJob._make_text_for_category(
                app_context=app_context,
                new_analytics=new_analytics,
                title=load('editorial_board_stats_job__title_author_search'),
                list_aliases=(
                    TrelloListAlias.TOPIC_READY,
                ),
                column_name='topic_ready'
            ),
            EditorialBoardVisualStatsJob._make_text_for_category(
                app_context=app_context,
                new_analytics=new_analytics,
                title=load('editorial_board_stats_job__title_in_work'),
                list_aliases=(
                    TrelloListAlias.IN_PROGRESS,
                ),
                column_name='in_progress'
            ),
            EditorialBoardVisualStatsJob._make_text_for_category(
                app_context=app_context,
                new_analytics=new_analytics,
                title=load('editorial_board_stats_job__title_deadline_missed'),
                list_aliases=(
                    TrelloListAlias.IN_PROGRESS,
                ),
                column_name='deadline_missed',
                filter_func=lambda card: card_checks.is_deadline_missed(card, app_context)[0]
            ),
            EditorialBoardVisualStatsJob._make_text_for_category(
                app_context=app_context,
                new_analytics=new_analytics,
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
            EditorialBoardVisualStatsJob._make_text_for_category(
                app_context=app_context,
                new_analytics=new_analytics,
                title=load('editorial_board_stats_job__title_waiting_for_editors'),
                list_aliases=(
                    TrelloListAlias.TO_EDITOR,
                ),
                column_name='waiting_for_editors',
            ),
            EditorialBoardVisualStatsJob._make_text_for_category(
                app_context=app_context,
                new_analytics=new_analytics,
                title=load('editorial_board_stats_job__title_editors_check'),
                list_aliases=(
                    TrelloListAlias.TO_SEO_EDITOR,
                    TrelloListAlias.EDITED_NEXT_WEEK,
                ),
                column_name='editors_check'
            ),
            EditorialBoardVisualStatsJob._make_text_for_category(
                app_context=app_context,
                new_analytics=new_analytics,
                title=load('editorial_board_stats_job__title_ready_to_issue'),
                list_aliases=(
                    TrelloListAlias.EDITED_SOMETIMES,
                    TrelloListAlias.TO_CHIEF_EDITOR,
                    TrelloListAlias.PROOFREADING,
                    TrelloListAlias.DONE,
                ),
                column_name='ready_to_issue'
            )
        ]

        date_interval = ''
        try:
            last_stats_date = utils.retrieve_last_trello_analytics_date(app_context.db_client)
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
        labels = [x.split(': ')[0] for x in stats]
        x = np.arange(len(labels))
        plt.xticks(rotation=90)
        # Note we add the `width` parameter now which sets the width of each bar.
        b1 = ax.bar(x, [int(x.split(': ')[1].strip('</b>')) for x in stats],
                    width=DEFAULT_BAR_WIDTH)
        # Same thing, but offset the x by the width of the bar.
        try:
            b2 = ax.bar(
                x + DEFAULT_BAR_WIDTH,
                [int(x.split(': ')[2].strip('</b>')) for x in stats],
                width=DEFAULT_BAR_WIDTH)
        except Exception:
            pass
        ax.set_ylabel('Count')
        ax.set_title('Visual Stats Board')
        ax.set_xticks(x, labels)
        ax.legend()

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
    def _make_text_for_category(
            app_context: AppContext,
            new_analytics: TrelloAnalytics,
            title: str,
            list_aliases: Tuple[str],
            column_name: str,
            filter_func=None,
    ) -> str:
        '''
        Returns a single string for category statistics (e.g. "В работе у авторов: 3")
        '''
        logger.info(f'Started counting: "{title}"')
        list_ids = app_context.trello_client.get_list_id_from_aliases(list_aliases)
        cards = list(filter(filter_func, app_context.trello_client.get_cards(list_ids)))
        statistics = utils.retrieve_last_trello_analytics(app_context.db_client)
        setattr(new_analytics, column_name, len(cards))

        size_and_delta = len(cards)
        if statistics:  # otherwise it's a first command run
            size_and_delta = f'{len(cards)}: {int(getattr(statistics, column_name))}'

        return load(
            'editorial_board_stats_job__title_and_delta',
            title=title,
            delta=size_and_delta
        )
