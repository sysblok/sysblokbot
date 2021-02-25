import pytest

import os

from conftest import SHEETS_TEST_DIR
from utils.json_loader import JsonLoader


json_loader = JsonLoader(os.path.join(SHEETS_TEST_DIR, 'expected'))


def test_init(mock_sheets_client):
    pass


def test_fetch_authors(mock_sheets_client):
    authors = [author.to_dict() for author in mock_sheets_client.fetch_authors()]
    json_loader.assert_equal(authors, 'authors.json')


def test_fetch_curators(mock_sheets_client):
    curators = [curator.to_dict() for curator in mock_sheets_client.fetch_curators()]
    json_loader.assert_equal(curators, 'curators.json')


def test_fetch_rubrics(mock_sheets_client):
    rubrics = [rubric.to_dict for rubric in mock_sheets_client.fetch_rubrics()]
    json_loader.assert_equal(rubrics, 'rubrics.json')


@pytest.mark.skip(reason="TODO")
def test_fill_posts_registry(mock_sheets_client):
    mock_sheets_client.update_posts_registry([])
