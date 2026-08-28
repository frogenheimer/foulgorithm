"""Shared source-adapter machinery.

Every adapter splits fetch from parse. Fetch writes raw bytes to data/raw/ and
returns them. Parse works on those bytes with no network access, so parser bugs
are replayable offline and development never re-hits a rate-limited source.

See docs/02-data-sources.md.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


class SourceError(Exception):
    """A source returned something we will not silently accept.

    Raised rather than defaulted. The 2025 version turned every failure into a
    neutral value, which made broken lookups indistinguishable from real data.
    """


@dataclass(frozen=True)
class RawResponse:
    source: str
    url: str
    content: bytes
    content_type: str
    status_code: int
    fetched_at: datetime

    def text(self) -> str:
        return self.content.decode("utf-8-sig", errors="replace")

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.content).hexdigest()[:16]

    def cache_path(self, root: Path, suffix: str = ".csv") -> Path:
        day = self.fetched_at.strftime("%Y-%m-%d")
        return root / self.source / day / f"{self.digest}{suffix}"

    def write_cache(self, root: Path, suffix: str = ".csv") -> Path:
        path = self.cache_path(root, suffix)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.content)
        return path


def utcnow() -> datetime:
    return datetime.now(UTC)
