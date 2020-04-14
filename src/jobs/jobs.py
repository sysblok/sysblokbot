"""
A module for business logic-containing regular jobs.
Jobs should use corresponding client objects to interact with
Trello, Spreadsheets or Telegram API.
Jobs can be ran from scheduler or from anywhere else for a one-off action.
"""

def sample_job(trello_client, sheets_client, telegram_sender):
    # Logic here could include retrieving data from trello/sheets
    # and sending a notification to corresponding user.
    print("I am a job and I'm done")


def manager_stats_job(trello_client, telegram_sender):
    telegram_sender.send_to_manager(
        str(list(map(str, trello_client.get_lists())))
    )
