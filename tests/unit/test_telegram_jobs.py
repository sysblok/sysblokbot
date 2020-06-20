import pytest

from freezegun import freeze_time
from typing import List

from src.app_context import AppContext
from src.config_manager import ConfigManager
from src import jobs
from src.tg.sender import TelegramSender
from src.trello.trello_client import TrelloClient

from fakes import fake_sender
from conftest import mock_sender


@freeze_time("2020-05-01 11:59:00")
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
        (
            jobs.editorial_report_job.EditorialReportJob,
            [
                'Отредактировано и ожидает финальной проверки: 0',
                'На доработке у автора: 0',
                'На редактуре: 3',
                'Ожидает редактуры: 3',
            ]
        ),
        # (
        #     jobs.fill_posts_list_job.FillPostsListJob,
        # ),
        # (
        #     jobs.illustrative_report_job.IllustrativeReportJob,
        # ),
        (
            jobs.db_fetch_authors_sheet_job.DBFetchAuthorsSheetJob,
            ['Fetched 2']
        ),
        (
            jobs.db_fetch_curators_sheet_job.DBFetchCuratorsSheetJob,
            ['Fetched 1']
        ),
    )
)
def test_job(monkeypatch, mock_trello, mock_sheets_client, mock_config_manager, mock_sender, job, output_parts):
    
    def send_to_chat_id(message_text: str, chat_id: int, **kwargs):
        for part in output_parts:
            assert part in message_text
    
    monkeypatch.setattr(
        mock_sender,
        'send_to_chat_id',
        send_to_chat_id
    )

    job._execute(
        AppContext(mock_config_manager),
        send=mock_sender.create_chat_ids_send(0)
    )


@freeze_time("2020-05-01 11:59:00")
@pytest.mark.xfail(strict=True)
@pytest.mark.parametrize(
    'job, output_parts',
    (
        (jobs.sample_job.SampleJob, ['Error']),
    )
)
def test_job_failed(monkeypatch, mock_trello, mock_sheets_client, mock_config_manager, mock_sender, job, output_parts):
    
    def send_to_chat_id(message_text: str, chat_id: int, **kwargs):
        for part in output_parts:
            assert part in message_text
    
    monkeypatch.setattr(
        mock_sender,
        'send_to_chat_id',
        send_to_chat_id
    )

    job._execute(
        AppContext(mock_config_manager),
        send=mock_sender.create_chat_ids_send(0)
    )
