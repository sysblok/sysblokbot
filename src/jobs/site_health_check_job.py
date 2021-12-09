import logging
from typing import Callable

from bs4 import BeautifulSoup
import requests

from ..app_context import AppContext
from ..strings import load
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class SiteHealthCheckJob(BaseJob):
    @staticmethod
    def _execute(app_context: AppContext, send: Callable[[str], None], called_from_handler=False):
        site_config = app_context.config_manager.get_site_config()
        index_url = site_config.get('index_url')
        page = requests.get(index_url)
        if page.status_code != 200:
            send(
                load(
                    'site_health_check_job__wrong_status_code',
                    status_code=page.status_code, url=index_url
                )
            )
            logger.error(f'Bad status code for {index_url}: {page.status_code}')
            return
        logger.info(f'Status code: {page.status_code}')

        soup = BeautifulSoup(page.content, 'html.parser')
        body_substring = site_config.get('body_substring')
        body_contents = soup.find('body').get_text()
        if body_substring not in body_contents:
            send(
                load(
                    'site_health_check_job__wrong_body',
                    substring=body_substring, url=index_url
                )
            )
            logger.error(f'Bad body contents for {index_url}')
            logger.warning(f'Html:\n\n{body_contents}')
            return
        logger.debug('Site contents look healthy')
        if called_from_handler:
            send(
                load(
                    'site_health_check_job__ok',
                    url=index_url,
                    substring=body_substring,
                    time_elapsed_ms=f'{page.elapsed.total_seconds() * 100:.3f}',
                    status_code=page.status_code
                )
            )
