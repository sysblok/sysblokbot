import datetime
import logging
from typing import Callable, List

from ..app_context import AppContext
from ..consts import BoardCardColor, TrelloCardColor
from ..strings import load
from ..tg.sender import TelegramSender, pretty_send
from ..trello.trello_objects import TrelloCard
from ..utils import card_checks, card_checks_focalboard
from .base_job import BaseJob
from .utils import get_cards_by_curator, retrieve_usernames

logger = logging.getLogger(__name__)


class TrelloBoardStateNotificationsJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext,
        send: Callable[[str], None],
        called_from_handler=False,
        *args,
        **kwargs,
    ):
        sender = TelegramSender()

        curator_cards = get_cards_by_curator(
            app_context, app_context.trello_client.deprecated
        )
        for curator, curator_cards in curator_cards.items():
            curator_name, curator_tg = curator
            card_paragraphs = []
            curator_cards.sort(key=lambda c: c.due if c.due else datetime.datetime.min)
            for card in curator_cards:
                if app_context.trello_client.deprecated:
                    reasons = card_checks_focalboard.make_card_failure_reasons(
                        card, app_context
                    )
                else:
                    reasons = card_checks.make_card_failure_reasons(card, app_context)
                card_paragraph = TrelloBoardStateNotificationsJob._format_card(
                    card,
                    reasons,
                    app_context,
                )
                if card_paragraph:
                    card_paragraphs.append(card_paragraph)
            if card_paragraphs:
                paragraphs = [
                    load("trello_board_state_notifications_job__intro")
                ] + card_paragraphs
                if called_from_handler:
                    pretty_send(paragraphs, send)

                if curator_tg is None:
                    logger.error(
                        f"Telegram for {curator_name} not found, could not send notification!"
                    )
                    continue
                if curator_tg.startswith("@"):
                    curator_tg = curator_tg[1:]
                try:
                    chat = app_context.db_client.get_chat_by_name(curator_tg)
                    if chat:  # and chat.is_curator: TMP fix
                        pretty_send(
                            paragraphs, lambda msg: sender.send_to_chat_id(msg, chat.id)
                        )
                        logger.error(
                            f"not an error: Sent board report to {curator_name}"
                        )
                        if called_from_handler:
                            pretty_send([f"curator report sent to {chat.title}"], send)
                    else:
                        logger.error(
                            f"Curator {curator_name} is not enrolled, could not send notifications"
                        )
                        pretty_send(paragraphs, lambda msg: sender.send_error_log(msg))
                except ValueError as e:
                    logger.error(f"Could not send to {curator_name}:", exc_info=e)

    @staticmethod
    def _format_card(
        card: TrelloCard, failure_reasons: List[str], app_context: AppContext
    ) -> str:
        if not failure_reasons:
            return None

        failure_reasons_formatted = ", ".join(failure_reasons)
        labels = (
            load(
                "trello_board_state_job__card_labels",
                names=", ".join(
                    # We filter BLACK cards as this is an auxiliary label
                    label.name
                    for label in card.labels
                    if label.color not in [TrelloCardColor.BLACK, BoardCardColor.BLACK]
                ),
            )
            if card.labels
            else ""
        )

        # Avoiding message overflow, strip explanations in ()
        list_name = card.lst.name + "("
        list_name = list_name[: list_name.find("(")].strip()

        members = (
            load(
                "trello_board_state_job__card_members",
                members=", ".join(
                    retrieve_usernames(card.members, app_context.db_client)
                ),
                curators="",
            )
            if card.members
            else ""
        )

        return load(
            "trello_board_state_job__card_2",
            failure_reasons=failure_reasons_formatted,
            url=card.url,
            name=card.name,
            labels=labels,
            list_name=list_name,
            members=members,
        )
