import pytest

import src.tg as tg
import src.jobs as jobs

from fakes import fake_sender

def test_sample_job(monkeypatch):
    monkeypatch.setattr(tg.sender, 'TelegramSender', fake_sender.FakeTelegramSender)

    assert jobs.sample_job.SampleJob._execute(None, tg.sender.TelegramSender().create_reply_send(update=lambda self: None)) == None