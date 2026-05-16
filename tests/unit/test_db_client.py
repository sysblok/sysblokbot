def test_init(mock_db_client):
    pass


def test_fetch_all(mock_db_client, mock_sheets_client):
    mock_db_client.fetch_all(mock_sheets_client)
