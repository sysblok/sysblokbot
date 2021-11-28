import json
import pytest
import os
from telethon import TelegramClient
from telethon.sessions import StringSession

# Your API ID, hash and session string here
with open('config_override.json') as config_override:
    print(json.load(config_override))
    config = json.load(config_override)['telegram']
    api_id = int(config['api_id'])
    api_hash = config['api_hash']
    api_session = config["api_session"]
    telegram_chat_id = int(config["error_logs_recipients"][0])
    telegram_bot_name = config.get("handle", '')


@pytest.fixture
async def client() -> TelegramClient:
    client = TelegramClient(
        StringSession(api_session), api_id, api_hash,
        sequential_updates=True
    )
    # Connect to the server
    await client.connect()
    # Issue a high level command to start receiving message
    await client.get_me()

    yield client

    await client.disconnect()
    await client.disconnected
