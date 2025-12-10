import logging
import time
from typing import Callable

from ..app_context import AppContext
from .base_job import BaseJob

logger = logging.getLogger(__name__)


class BackfillTelegramUserIdsJob(BaseJob):
    @staticmethod
    def _execute(
        app_context: AppContext, send: Callable[[str], None], called_from_handler=False
    ):
        """
        Backfill Telegram user IDs by resolving usernames from TeamMember records.
        Creates User records and links them to TeamMember records.

        This job:
        1. Finds TeamMembers with Telegram usernames but no User record
        2. Resolves usernames to user IDs via telethon
        3. Creates/updates User records
        4. Handles rate limiting with delays between requests
        """
        db_client = app_context.db_client
        tg_client = app_context.tg_client

        # Get all team members with telegram usernames
        team_members = db_client.get_all_members()
        members_with_telegram = [
            m
            for m in team_members
            if m.telegram and m.telegram.strip() and m.telegram != "#N/A"
        ]

        send(f"Found {len(members_with_telegram)} team members with Telegram usernames")

        resolved_count = 0
        created_count = 0
        linked_count = 0
        failed_count = 0
        skipped_count = 0

        for member in members_with_telegram:
            telegram_username = member.telegram.strip()

            # Normalize username (remove @ if present for storage)
            normalized_username = telegram_username.lstrip("@")

            # Check if User already exists for this team_member_id
            existing_user = db_client.get_user_by_team_member_id(member.id)

            if existing_user and existing_user.telegram_user_id:
                logger.debug(
                    f"User already exists with telegram_user_id for {member.name}"
                )
                skipped_count += 1
                continue

            # Check if User with this username already exists
            user_by_username = db_client.get_user_by_telegram_username(
                normalized_username
            )
            if user_by_username and user_by_username.telegram_user_id:
                # User exists but might not be linked to team_member
                if not user_by_username.team_member_id:
                    db_client.link_user_to_team_member(user_by_username.id, member.id)
                    linked_count += 1
                    logger.info(
                        f"Linked existing User {user_by_username.id} to TeamMember {member.id}"
                    )
                skipped_count += 1
                continue

            # Try to resolve username to user_id
            # Add delay to avoid rate limiting (telethon has limits)
            time.sleep(0.2)  # 200ms delay between requests

            result = tg_client.resolve_telegram_username(telegram_username)

            if not result:
                # Result is None if:
                # 1. Username doesn't exist (actual failure)
                # 2. Username resolves to a channel/group/bot (not a User)
                # The resolve_telegram_username method logs which case it is
                logger.warning(
                    f"Could not resolve username {telegram_username} for {member.name} "
                    f"(check logs above for details - may be a channel/group, not a user)"
                )
                failed_count += 1
                continue

            user_id, resolved_username = result
            resolved_count += 1

            # Normalize resolved username (remove @ if present)
            if resolved_username:
                resolved_username = resolved_username.lstrip("@")

            # Check if User with this telegram_user_id already exists
            user_by_tg_id = db_client.get_user_by_telegram_id(user_id)

            if user_by_tg_id:
                # User exists but might not be linked to team_member
                if not user_by_tg_id.team_member_id:
                    db_client.link_user_to_team_member(user_by_tg_id.id, member.id)
                    linked_count += 1
                    logger.info(
                        f"Linked existing User {user_by_tg_id.id} to TeamMember {member.id}"
                    )

                # Update username if it changed
                if (
                    resolved_username
                    and user_by_tg_id.telegram_username != resolved_username
                ):
                    user_by_tg_id.telegram_username = resolved_username
                    db_client.Session().commit()
            else:
                # Create new User
                user = db_client.upsert_user_from_telegram(
                    telegram_user_id=user_id,
                    telegram_username=resolved_username,
                    team_member_id=member.id,
                )
                created_count += 1
                logger.info(
                    f"Created User {user.id} for {member.name} (tg_id={user_id})"
                )

        summary = (
            f"Backfill complete:\n"
            f"  - Resolved: {resolved_count}\n"
            f"  - Created: {created_count}\n"
            f"  - Linked: {linked_count}\n"
            f"  - Skipped (already exists): {skipped_count}\n"
            f"  - Failed: {failed_count}"
        )
        send(summary)
        logger.info(summary)
