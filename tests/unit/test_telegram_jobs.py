import pytest
from freezegun import freeze_time

from src import jobs
from src.app_context import AppContext
from src.strings import load


@freeze_time("2020-05-01 11:59:00")
@pytest.mark.parametrize(
    "job, expected_text_key",
    (
        (jobs.sample_job.SampleJob, "sample_job__expected_response"),
        # (
        #     jobs.trello_board_state_job.TrelloBoardStateJob,
        #     [
        #         'Еженедельная сводка',
        #         'Не указан автор в карточке: 1',
        #         'Не указан срок в карточке: 2',
        #         'Не указан тег рубрики в карточке: 2',
        #         'Пропущен дедлайн: 0'
        #     ]
        # ),
        # (
        #     jobs.publication_plans_job.PublicationPlansJob,
        #     [
        #         'Не могу сгенерировать сводку',
        #         'Open Memory Map</a> не заполнено: название поста',
        #         'тестовая карточка</a> не заполнено: название поста',
        #         'тестовая карточка 1</a> не заполнено: название поста',
        #         'Пожалуйста, заполни'
        #     ]
        # ),
        # # (
        # #     jobs.fill_posts_list_job.FillPostsListJob,
        # # ),
        # (
        #     jobs.db_fetch_authors_sheet_job.DBFetchAuthorsSheetJob,
        #     ['Fetched 2']
        # ),
        # (
        #     jobs.db_fetch_curators_sheet_job.DBFetchCuratorsSheetJob,
        #     ['Fetched 1']
        # ),
    ),
)
@pytest.mark.xfail(reason="TODO: adapt to sheetfu")
def test_job(
    monkeypatch,
    mock_strings_db_client,
    mock_trello,
    mock_sheets_client,
    mock_config_manager,
    mock_sender,
    job,
    expected_text_key,
):
    def send_to_chat_id(message_text: str, chat_id: int, **kwargs):
        assert load(expected_text_key) == message_text

    monkeypatch.setattr(mock_sender, "send_to_chat_id", send_to_chat_id)

    job._execute(
        AppContext(mock_config_manager), send=mock_sender.create_chat_ids_send(0)
    )


@freeze_time("2020-05-01 11:59:00")
@pytest.mark.xfail(strict=True)
@pytest.mark.parametrize("job, output_parts", ((jobs.sample_job.SampleJob, ["Error"]),))
def test_job_failed(
    monkeypatch,
    mock_trello,
    mock_sheets_client,
    mock_config_manager,
    mock_sender,
    job,
    output_parts,
):
    def send_to_chat_id(message_text: str, chat_id: int, **kwargs):
        for part in output_parts:
            assert part in message_text

    monkeypatch.setattr(mock_sender, "send_to_chat_id", send_to_chat_id)

    job._execute(
        AppContext(mock_config_manager), send=mock_sender.create_chat_ids_send(0)
    )
