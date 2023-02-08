import json
import os
from typing import Dict

from deepdiff import DeepDiff


class JsonLoader:
    def __init__(self, base_path: str):
        self.base_path = base_path

    def load_json(self, filename: str) -> Dict:
        with open(os.path.join(self.base_path, filename), "r") as fin:
            return json.loads(fin.read())

    def assert_equal(self, response: object, expected_filename: str):
        expected_response = self.load_json(expected_filename)
        assert not DeepDiff(response, expected_response)
