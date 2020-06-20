import pytest

import os

from conftest import SHEETS_TEST_DIR
from utils.json_loader import JsonLoader


json_loader = JsonLoader(os.path.join(SHEETS_TEST_DIR, 'expected'))


def test_init(mock_sheets_client):
    pass


def test_fetch_authors(mock_sheets_client):
    authors = mock_sheets_client.fetch_authors()
    json_loader.assert_equal(authors, 'sheets_authors.json')


def test_fetch_curators(mock_sheets_client):
    curators = mock_sheets_client.fetch_curators()
    json_loader.assert_equal(curators, 'sheets_curators.json')


def test_fetch_rubrics_registry(mock_sheets_client):
    rubrics = mock_sheets_client.fetch_rubrics_registry()
    json_loader.assert_equal(rubrics, 'sheets_rubrics_registry.json')


@pytest.mark.skip(reason="TODO")
def test_fill_posts_registry(mock_sheets_client):
    mock_sheets_client.update_posts_registry([])
