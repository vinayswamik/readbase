from __future__ import annotations

from dataclasses import dataclass

from src.backend.application.services.exceptions import ValidationError


@dataclass(frozen=True)
class AuthUser:
    user_id: str
    email: str
    name: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.user_id,
            "email": self.email,
            "name": self.name,
        }


def normalize_email_key(email: str) -> str:
    normalized = email.strip().casefold()
    if not normalized or "@" not in normalized:
        raise ValidationError("Email address is required.")
    if len(normalized) > 320:
        raise ValidationError("Email address is too long.")
    return normalized
