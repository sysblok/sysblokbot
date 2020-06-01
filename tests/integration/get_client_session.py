from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os

# Your API ID and hash here
api_id = int(os.environ["TELEGRAM_APP_ID"])
api_hash = os.environ["TELEGRAM_APP_HASH"]

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print("Your session string is:", client.session.save())