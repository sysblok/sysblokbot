import pytest
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

# Your API ID, hash and session string here
api_id = int(os.environ["TELEGRAM_APP_ID"])
api_hash = os.environ["TELEGRAM_APP_HASH"]
session_str = os.environ["TELETHON_SESSION"]


@pytest.fixture
async def client() -> TelegramClient:
    client = TelegramClient(
        StringSession(session_str), api_id, api_hash, 
        sequential_updates=True
    )
    # Connect to the server
    await client.connect()
    # Issue a high level command to start receiving message
    await client.get_me()

    yield client

    await client.disconnect()
    await client.disconnected
