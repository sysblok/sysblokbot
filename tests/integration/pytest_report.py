from enum import Enum
import time

from src.utils.singleton import Singleton


class PytestTestStatus(str, Enum):
    OK = 'OK'
    FAILED = 'FAILED'


class PytestReport(Singleton):
    def __init__(self):
        if self.was_initialized():
            return
        self.time_start = time.time()
        self.data = {
            'ts': self.time_start,
            'tests': []
        }

    def mark_finish(self):
        self.data['time_elapsed'] = time.time() - self.time_start
