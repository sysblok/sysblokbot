import pytest

from src.app_context import AppContext
from src.config_manager import ConfigManager
from src import jobs
from src.tg.sender import TelegramSender
from src.sheets.sheets_client import GoogleSheetsClient
from src.trello.trello_client import TrelloClient

from fakes import fake_sender
from conftest import mock_sender


@pytest.mark.parametrize(
    'job, output_parts',
    (
        (jobs.sample_job.SampleJob, ['job', 'done']),
        (
            jobs.trello_board_state_job.TrelloBoardStateJob,
            [
                'Еженедельная сводка',
                'Не указан автор в карточке: 1',
                'Не указан срок в карточке: 2',
                'Не указан тег рубрики в карточке: 2',
                'Пропущен дедлайн: 0'
            ]
        ),
        (
            jobs.publication_plans_job.PublicationPlansJob,
            [
                'Не могу сгенерировать сводку',
                'Open Memory Map</a> не заполнено: название поста',
                'тестовая карточка</a> не заполнено: название поста',
                'тестовая карточка 1</a> не заполнено: название поста',
                'Пожалуйста, заполни'
            ]
        ),
    )
)
def test_job(monkeypatch, mock_trello, mock_sheets_client, mock_config_manager, job, output_parts):
    _update_from_config, _parse_gs_res = mock_sheets_client
    monkeypatch.setattr(ConfigManager, 'get_latest_config', mock_config_manager)
    monkeypatch.setattr(TrelloClient, '_make_request', mock_trello)
    monkeypatch.setattr(GoogleSheetsClient, '_update_from_config', _update_from_config)
    monkeypatch.setattr(GoogleSheetsClient, '_parse_gs_res', _parse_gs_res)
    monkeypatch.setattr(
        TelegramSender,
        'send_to_chat_id',
        mock_sender(output_parts)
    )

    job._execute(
        AppContext(ConfigManager()),
        send=TelegramSender({}, {}).create_chat_ids_send((0))
    )
