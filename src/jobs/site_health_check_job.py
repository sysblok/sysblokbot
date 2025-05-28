import logging
from typing import Callable

import requests
from bs4 import BeautifulSoup

from ..app_context import AppContext
from ..consts import KWARGS
from ..strings import load
from ..tg.sender import pretty_send
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class SiteHealthCheckJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext,
        send: Callable[[str], None],
        called_from_handler=False,
        *args,
        **kwargs,
    ):
        if called_from_handler:
            # TODO: refactor and move it to helper
            url = args
            schedules = app_context.config_manager.get_jobs_config(
                __name__.split(".")[-1]
            )
            if len(args) == 0:
                names = [schedule.get(KWARGS, {}).get("name") for schedule in schedules]
                pretty_send(
                    [f"Usage: /check_site_health name\nAvailable names: {names}"], send
                )
                return
            assert len(args) == 1
            name = args[0]
            for schedule in schedules:
                if schedule.get(KWARGS, {}).get("name") == name:
                    kwargs = schedule[KWARGS]
        url = kwargs.get("index_url")
        logger.debug(f"Checking site health for {kwargs.get('name')}: {url}")
        try:
            page = requests.get(url)
        except Exception as e:
            send(
                load(
                    "site_health_check_job__connection_error",
                    url=url,
                )
            )
            logger.error(f"Connection error for {url}", exc_info=e)
            return

        if page.status_code != 200:
            send(
                load(
                    "site_health_check_job__wrong_status_code",
                    status_code=page.status_code,
                    url=url,
                )
            )
            logger.error(f"Bad status code for {url}: {page.status_code}")
            return
        logger.info(f"Status code: {page.status_code}")

        soup = BeautifulSoup(page.content, "html.parser")
        body_substring = kwargs.get("body_substring")
        body_contents = soup.find("body").get_text()
        if body_substring not in body_contents:
            send(
                load(
                    "site_health_check_job__wrong_body",
                    substring=body_substring,
                    url=url,
                )
            )
            logger.error(f"Bad body contents for {url}")
            logger.warning(f"Html:\n\n{body_contents}")
            return
        logger.debug("Site content looks healthy")
        if called_from_handler:
            send(
                load(
                    "site_health_check_job__ok",
                    url=url,
                    substring=body_substring,
                    time_elapsed_ms=f"{page.elapsed.total_seconds() * 100:.3f}",
                    status_code=page.status_code,
                )
            )

    @staticmethod
    def _usage_muted():
        return True
