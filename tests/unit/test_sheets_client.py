import os

import pytest
from conftest import SHEETS_TEST_DIR
from utils.json_loader import JsonLoader

from src.sheets.sheets_client import GoogleSheetsClient

json_loader = JsonLoader(os.path.join(SHEETS_TEST_DIR, "expected"))


@pytest.fixture(autouse=True)
def reset_sheets_client_singleton():
    GoogleSheetsClient.drop_instance()
    yield
    GoogleSheetsClient.drop_instance()


def _make_sheets_client(monkeypatch, sheets_config):
    monkeypatch.setattr(GoogleSheetsClient, "_authorize", lambda self: None)
    return GoogleSheetsClient(sheets_config=sheets_config)


def _base_sheets_config(team_identity_sheet_key=None):
    config = {
        "api_key_path": "stub",
        "authors_sheet_key": "authors_sheet_key",
        "curators_sheet_key": "curators_sheet_key",
        "hr_sheet_key": "hr_sheet_key",
        "hr_pt_sheet_key": "hr_pt_sheet_key",
        "post_registry_sheet_key": "post_registry_sheet_key",
        "rubrics_registry_sheet_key": "rubrics_registry_sheet_key",
        "strings_sheet_key": "strings_sheet_key",
    }
    if team_identity_sheet_key is not None:
        config["team_identity_sheet_key"] = team_identity_sheet_key
    return config


def test_init(mock_sheets_client):
    pass


def test_fetch_hr_team_uses_identity_sheet_when_configured(monkeypatch):
    calls = []
    client = _make_sheets_client(
        monkeypatch,
        _base_sheets_config(team_identity_sheet_key="team_identity_sheet_key"),
    )

    def _fetch_table(self, sheet_key, sheet_name=None):
        calls.append((sheet_key, sheet_name))
        return "team table"

    monkeypatch.setattr(GoogleSheetsClient, "_fetch_table", _fetch_table)

    assert client.fetch_hr_team() == "team table"
    assert calls == [("team_identity_sheet_key", "team")]


def test_fetch_hr_team_falls_back_to_hr_sheet_without_identity_sheet(monkeypatch):
    calls = []
    client = _make_sheets_client(monkeypatch, _base_sheets_config())

    def _fetch_table(self, sheet_key, sheet_name=None):
        calls.append((sheet_key, sheet_name))
        return "legacy team table"

    monkeypatch.setattr(GoogleSheetsClient, "_fetch_table", _fetch_table)

    assert client.fetch_hr_team() == "legacy team table"
    assert calls == [("hr_sheet_key", "Команда (с заморозкой)")]


def test_fetch_hr_team_falls_back_for_placeholder_identity_sheet(monkeypatch):
    calls = []
    client = _make_sheets_client(
        monkeypatch,
        _base_sheets_config(
            team_identity_sheet_key="do_not_set_here_please_go_to_config_override"
        ),
    )

    def _fetch_table(self, sheet_key, sheet_name=None):
        calls.append((sheet_key, sheet_name))
        return "legacy team table"

    monkeypatch.setattr(GoogleSheetsClient, "_fetch_table", _fetch_table)

    assert client.fetch_hr_team() == "legacy team table"
    assert calls == [("hr_sheet_key", "Команда (с заморозкой)")]


def test_fetch_telegram_ids_requires_identity_sheet(monkeypatch):
    client = _make_sheets_client(monkeypatch, _base_sheets_config())

    with pytest.raises(ValueError, match="team_identity_sheet_key"):
        client.fetch_telegram_ids()


def test_fetch_telegram_ids_reads_telegram_tab(monkeypatch):
    calls = []
    client = _make_sheets_client(
        monkeypatch,
        _base_sheets_config(team_identity_sheet_key="team_identity_sheet_key"),
    )

    def _fetch_table(self, sheet_key, sheet_name=None):
        calls.append((sheet_key, sheet_name))
        return "telegram table"

    monkeypatch.setattr(GoogleSheetsClient, "_fetch_table", _fetch_table)

    assert client.fetch_telegram_ids() == "telegram table"
    assert calls == [("team_identity_sheet_key", "telegram")]


@pytest.mark.skip(reason="TODO")
def test_fetch_authors(mock_sheets_client):
    authors = [author.to_dict() for author in mock_sheets_client.fetch_authors()]
    json_loader.assert_equal(authors, "authors.json")


@pytest.mark.skip(reason="TODO")
def test_fetch_curators(mock_sheets_client):
    curators = [curator.to_dict() for curator in mock_sheets_client.fetch_curators()]
    json_loader.assert_equal(curators, "curators.json")


@pytest.mark.skip(reason="TODO")
def test_fetch_rubrics(mock_sheets_client):
    rubrics = [rubric.to_dict() for rubric in mock_sheets_client.fetch_rubrics()]
    json_loader.assert_equal(rubrics, "rubrics.json")


@pytest.mark.skip(reason="TODO")
def test_fill_posts_registry(mock_sheets_client):
    mock_sheets_client.update_posts_registry([])
