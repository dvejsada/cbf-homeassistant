"""Tests of the HA independent CBF parser."""

from __future__ import annotations

from datetime import date, datetime, time

import pytest

from custom_components.cbf.api import (
    CBF_TZ,
    CbfParseError,
    PhaseData,
    TeamView,
    default_season,
    filter_divisions,
    parse_divisions,
    parse_phase_reference,
    parse_schedule,
    parse_table,
)

from .conftest import TEAM_ID, load


@pytest.fixture
def phase() -> PhaseData:
    return PhaseData(
        games=tuple(parse_schedule(load("sched_10469.xml"))),
        table=tuple(parse_table(load("table_10469.xml"))),
    )


def test_parse_divisions() -> None:
    divisions = parse_divisions(load("divs_2026.xml"))
    div = next(d for d in divisions if d.id == 5382)
    assert div.name == "2.třída B"
    assert div.category == "muži"
    assert [p.id for p in div.phases] == [10469]
    # competitions without phases are filtered out
    assert all(d.phases for d in filter_divisions(divisions))
    assert [d.id for d in filter_divisions(divisions, search="2. třída b")] == [5382]


def test_parse_schedule(phase: PhaseData) -> None:
    assert len(phase.games) == 132
    first = phase.games[0]
    assert first.played
    assert first.home.name == "TJ Slavoj OS A"
    assert first.away.name == "Sokol Košíře"  # double space collapsed
    assert first.start == datetime(2026, 10, 7, 18, 30, tzinfo=CBF_TZ)
    assert first.partials == ((14, 22), (32, 41), (41, 52))
    assert first.quarters_for(first.home.id) == [(14, 22), (18, 19), (9, 11), (18, 19)]
    assert first.referees == ("Jan Lejčko", "Lucie Moravcová")


def test_unscheduled_and_unknown_time(phase: PhaseData) -> None:
    postponed = next(g for g in phase.games if g.id == 551856)
    assert postponed.game_date is None
    assert postponed.start is None
    tbc = [g for g in phase.games if g.game_date and g.game_time is None]
    assert tbc and all(not g.played for g in tbc)
    assert all(not g.partials for g in phase.games if not g.played)


def test_table(phase: PhaseData) -> None:
    view = TeamView(TEAM_ID, phase)
    row = view.standing
    assert row is not None
    assert (row.position, row.wins, row.losses, row.points) == (7, 2, 5, 9)
    assert row.team.name == "TJ ÚVN"


def test_team_view(phase: PhaseData) -> None:
    view = TeamView(TEAM_ID, phase)
    assert len(view.games) == 22
    now = datetime(2026, 11, 21, 12, 0, tzinfo=CBF_TZ)

    last = view.last_game
    assert last is not None and last.home.name == "HB Basket"
    assert last.score_for(TEAM_ID) == (54, 83)
    assert last.won(TEAM_ID) is False

    nxt = view.next_game(now)
    assert nxt is not None
    assert nxt.opponent(TEAM_ID).name == "Sokol Dolní Počernice C"
    assert view.next_transition(now) == nxt.start

    assert view.games_remaining == 15
    assert view.streak == "L2"
    assert not view.season_finished

    h2h = view.head_to_head(7814)  # TJ Slavoj OS A
    assert h2h["losses"] == 1 and h2h["games"][0]["score"] == "47:97"


def test_next_game_time_unknown(phase: PhaseData) -> None:
    view = TeamView(TEAM_ID, phase)
    now = datetime(2027, 1, 11, 20, 0, tzinfo=CBF_TZ)
    game = view.next_game(now)
    assert game is not None
    assert game.game_date == date(2027, 1, 11) and game.game_time is None
    assert view.next_transition(now) == datetime(2027, 1, 12, tzinfo=CBF_TZ)


def test_next_game_skips_awaiting_result(phase: PhaseData) -> None:
    view = TeamView(TEAM_ID, phase)
    # 2026-11-26 19:40 game has started -> next is 2026-12-01
    now = datetime(2026, 11, 26, 19, 41, tzinfo=CBF_TZ)
    game = view.next_game(now)
    assert game is not None and game.game_date == date(2026, 12, 1)
    assert game.game_time == time(19, 40)


def test_helpers() -> None:
    assert parse_phase_reference("10469") == 10469
    assert parse_phase_reference("https://www.cbf.cz/xml/sched.php?p=10469") == 10469
    assert parse_phase_reference("https://example.com/?s=1&p=42") == 42
    assert parse_phase_reference("nope") is None
    assert default_season(date(2026, 11, 21)) == 2026
    assert default_season(date(2027, 3, 1)) == 2026
    assert default_season(date(2027, 8, 1)) == 2027


def test_invalid_xml() -> None:
    with pytest.raises(CbfParseError):
        parse_schedule(b"<html>nope</html>")
    with pytest.raises(CbfParseError):
        parse_table(b"not xml")
