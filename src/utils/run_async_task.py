import logging
import threading
from typing import Callable, List

logger = logging.getLogger(__name__)


def _wrapper(function: Callable, results: List):
    results = []



def run_task(function: Callable):
    results = []



    if loop.is_running():
        task = loop.create_task(function())
        return await task
        