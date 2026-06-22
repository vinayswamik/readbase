from __future__ import annotations

import time
from dataclasses import dataclass

from sqlalchemy import select

from src.backend.infrastructure.database import session_scope
from src.backend.infrastructure.models import RateLimitBucket


@dataclass(frozen=True)
class RateLimitRule:
    max_requests: int
    window_seconds: int


class DatabaseRateLimiter:
    def allow(self, key: str, rule: RateLimitRule) -> bool:
        now = time.time()
        window_start = now - rule.window_seconds
        with session_scope() as session:
            record = session.get(RateLimitBucket, key)
            if record is None:
                session.add(
                    RateLimitBucket(
                        bucket_key=key,
                        window_start=now,
                        hit_count=1,
                    )
                )
                return True
            if record.window_start < window_start:
                record.window_start = now
                record.hit_count = 1
                return True
            if record.hit_count >= rule.max_requests:
                return False
            record.hit_count += 1
            return True

    def reset(self) -> None:
        with session_scope() as session:
            for record in session.scalars(select(RateLimitBucket)).all():
                session.delete(record)


_rate_limiter = DatabaseRateLimiter()


def allow_rate_limit(key: str, rule: RateLimitRule) -> bool:
    return _rate_limiter.allow(key, rule)


def reset_rate_limits() -> None:
    _rate_limiter.reset()
