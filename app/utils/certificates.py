
from datetime import datetime, timezone
from typing import Any, Optional

EXPIRING_SOON_THRESHOLD_DAYS = 30


def _parse_expiry(metadata: dict[str, Any]) -> Optional[datetime]:
    raw = metadata.get("expires") if metadata else None
    if not raw:
        return None
    try:
        # Accept plain dates ("2025-01-02") and full ISO timestamps.
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (ValueError, TypeError):
        return None


def get_certificate_status(
    metadata: dict[str, Any] | None,
    now: Optional[datetime] = None,
) -> Optional[str]:
   
    expiry = _parse_expiry(metadata or {})
    if expiry is None:
        return None

    now = now or datetime.now(timezone.utc)
    days_remaining = (expiry - now).days

    if days_remaining < 0:
        return "expired"
    if days_remaining <= EXPIRING_SOON_THRESHOLD_DAYS:
        return "expiring_soon"
    return "valid"
