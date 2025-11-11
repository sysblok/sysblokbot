import datetime
import logging
from typing import Callable, List

from ..focalboard.focalboard_client import FocalboardClient

from ..app_context import AppContext
from ..consts import BoardCardColor, BoardListAlias, TrelloCardColor
from ..strings import load
from ..tg.sender import pretty_send
from .base_job import BaseJob
from .utils import check_trello_card, format_errors, format_possibly_plural

logger = logging.getLogger(__name__)


class PublicationPlansJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        validation_errors = {}
        errors = {}

        paragraphs = [load("publication_plans_job__intro")]

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            focalboard_client=app_context.focalboard_client,
            title=load("publication_plans_job__title_publish_this_week"),
            list_aliases=(
                BoardListAlias.PUBLISH_BACKLOG_9,
                BoardListAlias.PUBLISH_IN_PROGRESS_10,
            ),
            errors=errors,
            validation_errors=validation_errors,
            show_due=True,
            need_illustrators=True,
            need_date=True,
        )

        paragraphs += PublicationPlansJob._retrieve_cards_for_paragraph(
            focalboard_client=app_context.focalboard_client,
            title=load("common_report__section_title_editorial_board"),
            list_aliases=(
                BoardListAlias.PUBLISH_BACKLOG_9,
                BoardListAlias.PUBLISH_IN_PROGRESS_10,
            ),
            errors=errors,
            validation_errors=validation_errors,
            show_due=False,
            need_illustrators=False,
            need_date=False,
        )

        if len(validation_errors) > 0:
            error_message = PublicationPlansJob._format_validation_errors(
                validation_errors
            )
            send(error_message)
            return

        paragraphs.append(load("publication_plans_job__outro"))

        if len(errors) > 0:
            paragraphs += format_errors(errors)

        pretty_send(paragraphs, send)

    @staticmethod
    def _format_validation_errors(validation_errors: dict) -> str:
        message_lines = [
            "Не удалось сгенерировать сводку. Пожалуйста, заполни требуемые поля в карточках и запусти генерацию снова."
        ]
        for card_name, missing_fields in validation_errors.items():
            fields_text = ", ".join(missing_fields)
            message_lines.append(
                f'– В карточке __"{card_name}"__ не заполнено: {fields_text}'
            )
        return "\n".join(message_lines)

    @staticmethod
    def _retrieve_cards_for_paragraph(
        focalboard_client: FocalboardClient,
        title: str,
        list_aliases: List[BoardListAlias],
        errors: dict,
        validation_errors: dict,
        show_due=True,
        need_illustrators=True,
        need_date=False,
    ) -> List[str]:
        logger.info(f'Started counting: "{title}"')
        list_ids = focalboard_client.get_list_id_from_aliases(list_aliases)
        cards = focalboard_client.get_cards(list_ids)
        if show_due:
            cards.sort(key=lambda card: card.due or datetime.datetime.min)
        parse_failure_counter = 0

        paragraphs = [
            load("common_report__list_title_and_size", title=title, length=len(cards))
        ]

        for card in cards:
            if not card:
                parse_failure_counter += 1
                continue

            card_fields = focalboard_client.get_custom_fields(card.id)
            display_name = card_fields.title or card.name
            label_names = [
                label.name
                for label in card.labels
                if label.color not in [TrelloCardColor.BLACK, BoardCardColor.BLACK]
            ]

            is_archive_card = load("common_trello_label__archive") in label_names

            missing_fields = []

            if not card_fields.title or not card_fields.title.strip():
                missing_fields.append("название")

            error_display_name = (
                card_fields.title.strip()
                if card_fields.title and card_fields.title.strip()
                else card.name
                if card.name and card.name.strip()
                else "Без названия"
            )

            if not card_fields.google_doc:
                missing_fields.append("ссылка на Google Doc")

            if (
                not card_fields.authors
                or len(card_fields.authors) == 0
                or not any(author and author.strip() for author in card_fields.authors)
            ):
                missing_fields.append("автор(-ы)")

            if (
                not card_fields.editors
                or len(card_fields.editors) == 0
                or not any(editor and editor.strip() for editor in card_fields.editors)
            ):
                missing_fields.append("редактор(-ы)")

            if not is_archive_card and (
                not card_fields.illustrators
                or len(card_fields.illustrators) == 0
                or not any(
                    illustrator and illustrator.strip()
                    for illustrator in card_fields.illustrators
                )
            ):
                missing_fields.append("иллюстратор(-ы)")

            if card.due is None:
                missing_fields.append("дата")

            if missing_fields:
                validation_errors[f"[{error_display_name}]({card.url})"] = (
                    missing_fields
                )

                continue

            card_is_ok = check_trello_card(
                card,
                errors,
                is_bad_title=False,
                is_bad_illustrators=False,
                is_bad_due_date=False,
            )

            if not card_is_ok:
                continue

            date = (
                load(
                    "common_report__card_date",
                    date=card.due.strftime("%d.%m (%a)").lower(),
                )
                if show_due
                else ""
            )

            paragraphs.append(
                load(
                    "publication_plans_job__card",
                    date=date,
                    url=card.url,
                    name=display_name,
                    authors=format_possibly_plural(
                        load("common_role__author"), card_fields.authors
                    ),
                    editors=format_possibly_plural(
                        load("common_role__editor"), card_fields.editors
                    ),
                    illustrators=format_possibly_plural(
                        load("common_role__illustrator"), card_fields.illustrators
                    ),
                )
            )

        if parse_failure_counter > 0:
            logger.error(f"Unparsed cards encountered: {parse_failure_counter}")
        return paragraphs
