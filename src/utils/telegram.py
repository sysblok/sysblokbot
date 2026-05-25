def normalize_telegram_username(username: object) -> str:
    if username is None:
        return ""
    return str(username).strip().lstrip("@").lower()
