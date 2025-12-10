import logging
import re

import requests

from ..utils.singleton import Singleton

logger = logging.getLogger(__name__)


class N8nClient(Singleton):
    def __init__(self, n8n_config=None):
        if self.was_initialized():
            return

        self._n8n_config = n8n_config
        self._update_from_config()
        logger.info("N8nClient successfully initialized")

    def _update_from_config(self):
        """Update attributes according to current self._n8n_config"""
        self.webhook_url = self._n8n_config.get("webhook_url", "")
        self.token = self._n8n_config.get("token", "")
        self.users = self._n8n_config.get("users", {})

    def send_webhook(self, user_id: int, query: str) -> None:
        """
        Send a webhook request to n8n with user and request information.

        Args:
            user_id: Telegram user ID
            query: The user's message query
        """
        if not self.webhook_url:
            logger.warning("N8n webhook URL not configured, skipping webhook call")
            return

        # Get user config from mapping (defaults to empty if not found)
        user_id_str = str(user_id)
        user_config = self.users.get(user_id_str, {})
        scopes = user_config.get("scopes", [])
        claims = user_config.get("claims", {})
        is_admin = user_config.get("isAdmin", False)

        # Build payload
        payload = {
            "user": {
                "id": user_id,
                "scopes": scopes,
                "claims": claims,
                "isAdmin": is_admin,
            },
            "request": {
                "query": query,
                "channel": "telegram",
            },
        }

        # Prepare headers - minimal headers to match curl behavior
        headers = {
            "Content-Type": "application/json",
        }

        # Add token as query parameter (as curl does)
        params = {}
        if self.token:
            params["token"] = self.token

        try:
            logger.debug(
                f"Sending n8n webhook to: {self.webhook_url} "
                f"(token present: {bool(self.token)})"
            )

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers=headers,
                params=params,
                timeout=10,
            )

            # Log response details for debugging
            logger.debug(f"N8n webhook response: status={response.status_code}")
            response.raise_for_status()
            logger.debug(f"N8n webhook sent successfully for user {user_id}")
        except requests.exceptions.HTTPError as e:
            # 404 means webhook endpoint doesn't exist (expected during setup)
            if e.response.status_code == 404:
                logger.warning(
                    f"N8n webhook endpoint not found (404) for user {user_id}. "
                    "Webhook may not be set up yet."
                )
            else:
                # Redact token from error message
                error_msg = str(e)
                # Replace token in URL (both ?token= and &token=)
                error_msg = re.sub(r"[?&]token=[^&\s]+", r"?token=REDACTED", error_msg)

                # Log response body for debugging
                try:
                    response_body = e.response.text[:500]  # First 500 chars
                    logger.error(
                        f"Failed to send n8n webhook for user {user_id}: {error_msg}. "
                        f"Response body: {response_body}"
                    )
                except Exception:
                    logger.error(
                        f"Failed to send n8n webhook for user {user_id}: {error_msg}",
                        exc_info=True,
                    )
        except requests.exceptions.RequestException as e:
            # Redact token from error message
            error_msg = str(e)
            error_msg = re.sub(r"[?&]token=[^&\s]+", r"?token=REDACTED", error_msg)
            logger.error(
                f"Failed to send n8n webhook for user {user_id}: {error_msg}",
                exc_info=True,
            )

    def update_config(self, new_n8n_config):
        """To be called after config automatic update"""
        self._n8n_config = new_n8n_config
        self._update_from_config()
