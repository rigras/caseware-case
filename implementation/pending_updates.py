"""The pending-updates rule: what the list shows, what the review offers, and how a
decision changes an engagement's row (design.md §1; decisions.html D1, D4, D5).

Pure functions over plain values: no database, no engagement loading. The Pending
Updates API, the engagement hook and the backfill job would all call into this module.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from typing import Iterable, Optional, Sequence, Tuple


class Status(Enum):
    VERIFYING = "verifying"  # version not known yet (backfill pending)
    VERIFIED = "verified"
    ERROR = "error"  # engagement could not be loaded after 3 attempts
    ARCHIVED = "archived"


@dataclass(frozen=True)
class EngagementRow:
    """One row of engagement_versions (stored in the firm's own database)."""

    engagement_id: str
    template_id: Optional[str]
    current: Optional[int]  # template version the engagement is on
    declined_up_to: int  # highest version already reviewed; only rises
    revision: int  # the engagement's own save counter; newer wins
    status: Status


@dataclass(frozen=True)
class ListStatus:
    label: str  # "up_to_date" | "pending" | "verifying" | "error" | "archived"
    pending: Tuple[int, ...] = ()


@dataclass(frozen=True)
class SummaryRef:
    version: int  # show release_summaries row for this version (previous -> version)
    previously_declined: bool  # "previously declined, would be included"


@dataclass(frozen=True)
class Review:
    offers: Tuple[int, ...]  # versions the user can apply up to, latest first (walk-back order)
    summaries: Tuple[SummaryRef, ...]  # every version that would come in, oldest first


@dataclass(frozen=True)
class DecisionEntry:
    """One append-only row of decision_log."""

    engagement_id: str
    user: str
    at: datetime
    from_version: int
    applied_to: Optional[int]  # None = declined everything
    reviewed_up_to: int


@dataclass(frozen=True)
class CitationResult:
    invented: Tuple[str, ...]  # cited by the summary but not in the diff
    missing: Tuple[str, ...]  # in the diff but not cited by the summary

    @property
    def ok(self) -> bool:
        return not self.invented and not self.missing


def _pending(row: EngagementRow, published: Iterable[int]) -> Tuple[int, ...]:
    floor = max(row.current, row.declined_up_to)
    return tuple(sorted(v for v in set(published) if v > floor))


def list_status(row: EngagementRow, published: Sequence[int]) -> ListStatus:
    """What the engagement list shows. `published` = versions of the row's template."""
    if row.status is not Status.VERIFIED:
        return ListStatus(row.status.value)
    pending = _pending(row, published)
    return ListStatus("pending", pending) if pending else ListStatus("up_to_date")


def review(row: EngagementRow, published: Sequence[int]) -> Review:
    """What the review screen offers for an engagement with pending updates."""
    status = list_status(row, published)
    if status.label != "pending":
        raise ValueError(f"nothing to review: engagement is {status.label}")
    latest = status.pending[-1]
    incoming = sorted(v for v in set(published) if row.current < v <= latest)
    return Review(
        offers=tuple(reversed(status.pending)),
        summaries=tuple(SummaryRef(v, v <= row.declined_up_to) for v in incoming),
    )


def decide(
    row: EngagementRow,
    published: Sequence[int],
    applied_to: Optional[int],
    reviewed_up_to: int,
    revision: int,
    user: str,
    at: datetime,
) -> Tuple[EngagementRow, DecisionEntry]:
    """Record one review: apply up to `applied_to`, or decline everything (None).

    `reviewed_up_to` is the latest version the review screen showed; a version published
    while the user was reviewing stays pending instead of being declined unseen.
    `revision` is the engagement's own revision after this save (plain saves never reach
    our table, so it cannot be derived from the row); it is what makes an older backfill
    reading lose against this decision.

    Returns the new row and the decision_log entry; the engagement hook writes both in
    the same transaction as the engagement change.
    """
    offers = review(row, published).offers
    if revision <= row.revision:
        raise ValueError(f"revision {revision} is not newer than the row's {row.revision}")
    if reviewed_up_to not in offers:
        raise ValueError(f"v{reviewed_up_to} was not on offer; offered: {offers}")
    if applied_to is not None and (applied_to not in offers or applied_to > reviewed_up_to):
        raise ValueError(f"v{applied_to} is not offered up to v{reviewed_up_to}; offered: {offers}")
    new_row = replace(
        row,
        current=applied_to if applied_to is not None else row.current,
        declined_up_to=max(row.declined_up_to, reviewed_up_to),
        revision=revision,
    )
    entry = DecisionEntry(row.engagement_id, user, at, row.current, applied_to, reviewed_up_to)
    return new_row, entry


def record_observation(
    row: EngagementRow, template_id: str, version: int, revision: int
) -> EngagementRow:
    """Record the version read by loading the engagement (backfill job or a user opening it).

    Applied only if the reading is newer than what the row holds, so a slow backfill
    load can never overwrite an apply that happened meanwhile. Declines are never touched.
    """
    if row.status is Status.ARCHIVED or revision <= row.revision:
        return row
    return replace(
        row, template_id=template_id, current=version, revision=revision, status=Status.VERIFIED
    )


def check_citations(change_ids: Sequence[str], cited_ids: Sequence[str]) -> CitationResult:
    """The summary must cite every change of the diff and no change that does not exist."""
    changes, cited = set(change_ids), set(cited_ids)
    return CitationResult(
        invented=tuple(sorted(cited - changes)), missing=tuple(sorted(changes - cited))
    )
