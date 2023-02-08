import json
import os

from deepdiff import DeepDiff
from typing import Dict


class JsonLoader:
    def __init__(self, base_path: str):
        self.base_path = base_path

    def load_json(self, filename: str) -> Dict:
        with open(os.path.join(self.base_path, filename), 'r', encoding='utf-8') as fin:
            return json.loads(fin.read())

    def assert_equal(self, response: object, expected_filename: str):
        expected_response = self.load_json(expected_filename)
        assert not DeepDiff(response, expected_response)
