"""Tests for the pending-updates rule (design.md §1, decisions.html D1, D4, D5)."""

import random
from datetime import datetime

import pytest

from pending_updates import (
    EngagementRow,
    Status,
    check_citations,
    decide,
    list_status,
    record_observation,
    review,
)

AT = datetime(2026, 9, 18, 10, 0)


def row(current, declined_up_to=0, status=Status.VERIFIED, revision=1):
    return EngagementRow("smith-2026", "audit-canada", current, declined_up_to, revision, status)


# --- What the list shows -------------------------------------------------

def test_up_to_date_when_on_latest():
    s = list_status(row(5), published=[1, 2, 3, 4, 5])
    assert s.label == "up_to_date" and s.pending == ()


def test_accumulated_versions_are_all_pending():
    s = list_status(row(3), published=[1, 2, 3, 4, 5])
    assert s.label == "pending" and s.pending == (4, 5)


def test_declined_versions_are_not_pending_again():
    s = list_status(row(4, declined_up_to=5), published=[1, 2, 3, 4, 5])
    assert s.label == "up_to_date"


def test_published_order_does_not_matter():
    assert list_status(row(3), published=[5, 1, 4, 3, 2]).pending == (4, 5)


@pytest.mark.parametrize("status,label", [
    (Status.VERIFYING, "verifying"),
    (Status.ERROR, "error"),
    (Status.ARCHIVED, "archived"),
])
def test_unverified_rows_are_never_up_to_date(status, label):
    s = list_status(row(None, status=status), published=[1, 2])
    assert s.label == label and s.pending == ()


# --- What the review offers ----------------------------------------------

def test_review_offers_latest_first_then_walks_back():
    r = review(row(3), published=[3, 4, 5])
    assert r.offers == (5, 4)


def test_review_shows_one_summary_per_version_oldest_first():
    r = review(row(3), published=[3, 4, 5])
    assert [(s.version, s.previously_declined) for s in r.summaries] == [(4, False), (5, False)]


def test_review_marks_previously_declined_versions_that_would_come_in():
    # On v4, declined v5, v6 published: only v6 is offered, but v5's changes come in with it.
    r = review(row(4, declined_up_to=5), published=[4, 5, 6])
    assert r.offers == (6,)
    assert [(s.version, s.previously_declined) for s in r.summaries] == [(5, True), (6, False)]


def test_review_of_engagement_without_pending_updates_is_rejected():
    with pytest.raises(ValueError):
        review(row(5), published=[4, 5])


# --- Recording the decision -----------------------------------------------

def test_the_design_example_end_to_end():
    published = [3, 4, 5]
    eng = row(3)
    # User declines v5, then applies v4.
    eng, entry = decide(eng, published, applied_to=4, reviewed_up_to=5, revision=2, user="ana@abc", at=AT)
    assert (eng.current, eng.declined_up_to) == (4, 5)
    assert (entry.from_version, entry.applied_to, entry.reviewed_up_to) == (3, 4, 5)
    assert list_status(eng, published).label == "up_to_date"
    # v6 ships: one update pending, v5 shown as previously declined.
    published.append(6)
    assert list_status(eng, published).pending == (6,)
    # User declines everything: v5 and v6 are not offered again.
    eng, entry = decide(eng, published, applied_to=None, reviewed_up_to=6, revision=3, user="luis@abc", at=AT)
    assert (eng.current, eng.declined_up_to) == (4, 6)
    assert entry.applied_to is None
    assert list_status(eng, published).label == "up_to_date"


def test_apply_all_moves_to_latest():
    eng, _ = decide(row(3), [3, 4, 5], applied_to=5, reviewed_up_to=5, revision=2, user="ana@abc", at=AT)
    assert (eng.current, eng.declined_up_to) == (5, 5)


def test_decision_stores_the_engagements_own_revision():
    eng, _ = decide(row(3, revision=7), [3, 4, 5], applied_to=5, reviewed_up_to=5, revision=12,
                    user="ana@abc", at=AT)
    assert eng.revision == 12


def test_decision_with_a_revision_that_is_not_newer_is_rejected():
    with pytest.raises(ValueError):
        decide(row(3, revision=7), [3, 4, 5], applied_to=5, reviewed_up_to=5, revision=7,
               user="ana@abc", at=AT)


@pytest.mark.parametrize("applied_to", [3, 2, 6])
def test_cannot_apply_a_version_that_is_not_offered(applied_to):
    with pytest.raises(ValueError):
        decide(row(3), [3, 4, 5], applied_to=applied_to, reviewed_up_to=5, revision=2, user="ana@abc", at=AT)


def test_cannot_apply_a_previously_declined_version_on_its_own():
    with pytest.raises(ValueError):
        decide(row(4, declined_up_to=5), [4, 5, 6], applied_to=5, reviewed_up_to=6, revision=2,
               user="ana@abc", at=AT)


def test_cannot_decide_on_unverified_engagement():
    with pytest.raises(ValueError):
        decide(row(None, status=Status.VERIFYING), [1, 2], applied_to=2, reviewed_up_to=2, revision=2,
               user="ana@abc", at=AT)


# --- Backfill and open: an older reading never overwrites a newer one ----

def test_observation_fills_a_verifying_row():
    eng = record_observation(row(None, status=Status.VERIFYING, revision=0), "audit-canada", 3, revision=4)
    assert (eng.current, eng.revision, eng.status) == (3, 4, Status.VERIFIED)


def test_stale_observation_is_ignored():
    # Backfill read v3 at revision 4; meanwhile the user applied v4 (revision 5).
    eng = row(4, revision=5)
    assert record_observation(eng, "audit-canada", 3, revision=4) == eng


def test_observation_never_touches_declines():
    eng = record_observation(row(3, declined_up_to=5, revision=1), "audit-canada", 4, revision=2)
    assert eng.declined_up_to == 5


def test_observation_does_not_resurrect_archived_rows():
    eng = row(3, status=Status.ARCHIVED, revision=1)
    assert record_observation(eng, "audit-canada", 3, revision=9) == eng


def test_stale_backfill_reading_after_unseen_saves_does_not_undo_an_apply():
    # Our row saw the engagement at revision 10 (user opened it). The user then saved
    # work twice (revisions 11, 12: plain saves never reach our table) and applied v4
    # (revision 13). A backfill load that read v3 at revision 12 arrives afterwards.
    eng = row(3, revision=10)
    eng, _ = decide(eng, [3, 4], applied_to=4, reviewed_up_to=4, revision=13, user="ana@abc", at=AT)
    eng = record_observation(eng, "audit-canada", 3, revision=12)
    assert eng.current == 4


def test_version_published_during_review_is_not_declined_unseen():
    # The review showed v4 and v5; v6 is published before the user clicks "Apply up to v5".
    eng, entry = decide(row(3), [3, 4, 5, 6], applied_to=5, reviewed_up_to=5, revision=2,
                        user="ana@abc", at=AT)
    assert (eng.current, eng.declined_up_to, entry.reviewed_up_to) == (5, 5, 5)
    assert list_status(eng, [3, 4, 5, 6]).pending == (6,)


@pytest.mark.parametrize("applied_to,reviewed_up_to", [(5, 4), (4, 7), (None, 3)])
def test_reviewed_up_to_must_be_an_offered_version_at_or_above_the_applied_one(applied_to, reviewed_up_to):
    with pytest.raises(ValueError):
        decide(row(3), [3, 4, 5], applied_to=applied_to, reviewed_up_to=reviewed_up_to, revision=2,
               user="ana@abc", at=AT)


# --- Summary check: nothing invented, nothing missing (D5) ----------------

def test_citations_ok_when_every_change_cited_once_or_more():
    assert check_citations(["C1", "C2"], ["C2", "C1", "C1"]).ok


def test_citations_flag_invented_and_missing():
    r = check_citations(["C1", "C2", "C3"], ["C1", "C9"])
    assert not r.ok and r.invented == ("C9",) and r.missing == ("C2", "C3")


# --- Invariants over random histories ------------------------------------

def test_invariants_hold_over_random_histories():
    """Replays random interleavings of what happens in production: publications (also
    while a review is open), plain saves that never reach our table, decisions, and
    backfill readings that arrive late with an old revision."""
    rng = random.Random(42)
    for _ in range(500):
        published = [1]
        eng_revision = 1  # the engagement's own save counter
        eng = row(1, revision=eng_revision)
        in_flight = []  # backfill readings taken earlier: (version, revision)
        seen_by_user = set()  # versions some review has shown
        for _ in range(rng.randint(1, 20)):
            event = rng.random()
            if event < 0.3:
                published.append(published[-1] + 1)
            elif event < 0.45:
                eng_revision += 1  # plain save
            elif event < 0.6:
                in_flight.append((eng.current, eng_revision))  # backfill loads it now
            elif event < 0.75 and in_flight:
                before = eng
                version, revision = in_flight.pop(rng.randrange(len(in_flight)))
                eng = record_observation(eng, "audit-canada", version, revision)
                assert eng.current >= before.current, "a late reading moved the engagement back"
            elif list_status(eng, published).label == "pending":
                r = review(eng, published)
                seen_by_user.update(r.offers)
                reviewed_up_to = r.offers[0]
                if rng.random() < 0.3:
                    published.append(published[-1] + 1)  # published while the review is open
                applied_to = rng.choice([None, *r.offers])
                eng_revision += 1
                before = eng
                eng, entry = decide(eng, published, applied_to, reviewed_up_to, eng_revision,
                                    user="u", at=AT)
                assert eng.current >= before.current, "a decision moved the engagement back"
                assert eng.declined_up_to >= before.declined_up_to
                # Exactly the versions nobody has reviewed yet are still pending.
                assert list_status(eng, published).pending == tuple(
                    v for v in published if v > reviewed_up_to)
            # Nothing is ever skipped unseen: every version at or below the floor was
            # either applied or shown in a review.
            floor = max(eng.current, eng.declined_up_to)
            assert all(v in seen_by_user or v <= eng.current for v in published if v <= floor)
