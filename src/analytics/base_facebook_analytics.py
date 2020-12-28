from datetime import datetime


class BaseFacebookAnalytics:

    def get_new_posts_count(self, since: datetime, until: datetime):
        """
        Get the number of new posts for the period.
        """
        raise NotImplementedError('')

    def get_weekly_total_reach_of_new_posts(self, end_week: datetime):
        """
        Get weekly statistics on the total reach of new posts
        """
        raise NotImplementedError('')

    def get_weekly_organic_reach_of_new_posts(self, end_week: datetime):
        """
        Get weekly statistics on the organic reach of new posts
        """
        raise NotImplementedError('')
