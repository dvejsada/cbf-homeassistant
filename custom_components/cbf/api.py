"""Client and parser for the CBF (Czech Basketball Federation) XML exports.

This module intentionally has no Home Assistant imports so it can be unit tested
on its own. Documentation of the exports: https://cbf.cz.basketball/xml-exporty/p58
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from datetime import date, datetime, time, timedelta
import re
from typing import Any
from xml.etree.ElementTree import Element
from zoneinfo import ZoneInfo

import aiohttp
from defusedxml import ElementTree as DefusedET

BASE_URL = "https://www.cbf.cz/xml/"
CBF_TZ = ZoneInfo("Europe/Prague")
USER_AGENT = "HomeAssistant-CBF/1.0 (+https://github.com/dvejsada/cbf-homeassistant)"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)

#: Assumed duration of a game, used for calendar events.
GAME_DURATION = timedelta(hours=2)


class CbfError(Exception):
    """Base error of the CBF client."""


class CbfConnectionError(CbfError):
    """The CBF server could not be reached or returned an error."""


class CbfParseError(CbfError):
    """The CBF server returned data that could not be parsed."""


def clean(text: str | None) -> str:
    """Collapse the irregular whitespace found in CBF names."""
    return " ".join((text or "").split())


def _int(text: str | None, default: int = 0) -> int:
    try:
        return int((text or "").strip())
    except ValueError:
        return default


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Phase:
    """A phase of a competition (e.g. regular season, play-off)."""

    id: int
    name: str


@dataclass(frozen=True, slots=True)
class Division:
    """A competition in a season."""

    id: int
    name: str
    category: str
    league: str
    phases: tuple[Phase, ...]

    @property
    def label(self) -> str:
        """Human readable label distinguishing equally named competitions."""
        return f"{self.name} · {self.category} · {self.league}"


@dataclass(frozen=True, slots=True)
class Team:
    """A team ("družstvo")."""

    id: int
    name: str


@dataclass(frozen=True, slots=True)
class Game:
    """A game of a phase."""

    id: int
    round: str
    game_date: date | None
    game_time: time | None
    venue: str
    city: str
    home: Team
    away: Team
    home_points: int
    away_points: int
    home_score: int
    away_score: int
    #: Cumulative running score after each period, as (home, away).
    partials: tuple[tuple[int, int], ...] = ()
    referees: tuple[str, ...] = ()

    @property
    def played(self) -> bool:
        """Return True if a result was entered.

        Unplayed games have a 0:0 score *and* a 0:0 placeholder partial, the table
        points (``pts``) are the reliable indicator.
        """
        return (self.home_points, self.away_points) != (0, 0) or (
            self.home_score,
            self.away_score,
        ) != (0, 0)

    @property
    def scheduled(self) -> bool:
        """Return True if the game has a date."""
        return self.game_date is not None

    @property
    def time_known(self) -> bool:
        """Return True if the tip-off time is known."""
        return self.game_time is not None

    @property
    def start(self) -> datetime | None:
        """Timezone aware tip-off, if both date and time are known."""
        if self.game_date is None or self.game_time is None:
            return None
        return datetime.combine(self.game_date, self.game_time, tzinfo=CBF_TZ)

    @property
    def sort_key(self) -> tuple[date, time]:
        """Chronological sort key; unscheduled games sort last."""
        return (self.game_date or date.max, self.game_time or time.min)

    @property
    def location(self) -> str:
        """Venue and city."""
        return ", ".join(part for part in (self.venue, self.city) if part)

    def involves(self, team_id: int) -> bool:
        """Return True if the team plays in this game."""
        return team_id in (self.home.id, self.away.id)

    def is_home(self, team_id: int) -> bool:
        """Return True if the team is the home team."""
        return self.home.id == team_id

    def opponent(self, team_id: int) -> Team:
        """Return the opponent of the team."""
        return self.away if self.is_home(team_id) else self.home

    def score_for(self, team_id: int) -> tuple[int, int]:
        """Return (team score, opponent score)."""
        if self.is_home(team_id):
            return self.home_score, self.away_score
        return self.away_score, self.home_score

    def won(self, team_id: int) -> bool | None:
        """Return True/False for win/loss, None if not played or a draw."""
        if not self.played:
            return None
        own, opp = self.score_for(team_id)
        if own == opp:
            own_pts, opp_pts = (
                (self.home_points, self.away_points)
                if self.is_home(team_id)
                else (self.away_points, self.home_points)
            )
            if own_pts == opp_pts:
                return None
            return own_pts > opp_pts
        return own > opp

    def quarters_for(self, team_id: int) -> list[tuple[int, int]]:
        """Return per-period scores (team, opponent) derived from cumulative partials.

        The export contains the running score after periods 1..n-1, the last
        period is derived from the final score. Overtime cannot be distinguished.
        """
        if not self.played or not self.partials:
            return []
        home_first = self.is_home(team_id)
        cumulative = [*self.partials, (self.home_score, self.away_score)]
        result: list[tuple[int, int]] = []
        prev = (0, 0)
        for home, away in cumulative:
            if (home, away) < prev:  # inconsistent data, give up
                return []
            diff = (home - prev[0], away - prev[1])
            result.append(diff if home_first else (diff[1], diff[0]))
            prev = (home, away)
        return result


@dataclass(frozen=True, slots=True)
class Standing:
    """A row of the standings table."""

    position: int
    team: Team
    games_played: int
    wins: int
    losses: int
    points_scored: int
    points_conceded: int
    points: int

    @property
    def point_difference(self) -> int:
        """Scored minus conceded."""
        return self.points_scored - self.points_conceded

    def as_dict(self) -> dict[str, Any]:
        """Serialise for state attributes."""
        return {
            "position": self.position,
            "team": self.team.name,
            "team_id": self.team.id,
            "games_played": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
            "points_scored": self.points_scored,
            "points_conceded": self.points_conceded,
            "point_difference": self.point_difference,
            "points": self.points,
        }


@dataclass(frozen=True, slots=True)
class PhaseData:
    """Everything fetched for a phase."""

    games: tuple[Game, ...]
    table: tuple[Standing, ...] = field(default_factory=tuple)

    @property
    def results_signature(self) -> tuple[tuple[int, int, int], ...]:
        """Identifies the set of entered results; changes when a result is added."""
        return tuple(
            (g.id, g.home_score, g.away_score) for g in self.games if g.played
        )

    def teams(self) -> list[Team]:
        """Teams of the phase, from the table or (fallback) the schedule."""
        if self.table:
            return [row.team for row in self.table]
        seen: dict[int, Team] = {}
        for game in self.games:
            for team in (game.home, game.away):
                seen.setdefault(team.id, team)
        return sorted(seen.values(), key=lambda t: t.name.casefold())


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------


def _parse_root(payload: bytes, expected: str) -> Element:
    try:
        root = DefusedET.fromstring(payload)
    except Exception as err:  # defusedxml raises several exception types
        raise CbfParseError(f"Invalid XML: {err}") from err
    if root.tag != expected:
        raise CbfParseError(f"Unexpected root element <{root.tag}>")
    return root


def _team(node: Element | None) -> Team:
    if node is None:
        return Team(0, "")
    return Team(_int(node.findtext("id")), clean(node.findtext("name")))


def _parse_date(text: str | None) -> date | None:
    try:
        return date.fromisoformat((text or "").strip())
    except ValueError:  # "0000-00-00" for postponed games
        return None


def _parse_time(text: str | None) -> time | None:
    try:
        value = time.fromisoformat((text or "").strip())
    except ValueError:
        return None
    if value == time(0, 0):  # 00:00:00 means "not set yet"
        return None
    return value


def parse_divisions(payload: bytes) -> list[Division]:
    """Parse ``divs.php`` output."""
    root = _parse_root(payload, "divs")
    divisions = []
    for node in root.findall("div"):
        phases = tuple(
            Phase(_int(p.findtext("id")), clean(p.findtext("name")))
            for p in node.findall("phases/phase")
        )
        divisions.append(
            Division(
                id=_int(node.findtext("id")),
                name=clean(node.findtext("name")),
                category=clean(node.findtext("cat/name")),
                league=clean(node.findtext("league/name")),
                phases=phases,
            )
        )
    return divisions


def parse_schedule(payload: bytes) -> list[Game]:
    """Parse ``sched.php`` output."""
    root = _parse_root(payload, "games")
    games = []
    for node in root.findall("game"):
        teams = node.findall("team")
        home = next((t for t in teams if t.get("guest") == "0"), None)
        away = next((t for t in teams if t.get("guest") == "1"), None)
        if home is None and away is None and len(teams) == 2:
            home, away = teams
        refs = sorted(node.findall("ref"), key=lambda r: _int(r.get("ord")))
        partials = tuple(
            (_int(p.findtext("a")), _int(p.findtext("b")))
            for p in sorted(
                node.findall("result/partials/partial"),
                key=lambda p: _int(p.get("ord")),
            )
        )
        game = Game(
            id=_int(node.findtext("id")),
            round=clean(node.findtext("round")) or clean(node.findtext("xround")),
            game_date=_parse_date(node.findtext("gdate")),
            game_time=_parse_time(node.findtext("gtime")),
            venue=clean(node.findtext("place")),
            city=clean(node.findtext("city")),
            home=_team(home),
            away=_team(away),
            home_points=_int(node.findtext("result/pts/a")),
            away_points=_int(node.findtext("result/pts/b")),
            home_score=_int(node.findtext("result/score/a")),
            away_score=_int(node.findtext("result/score/b")),
            partials=(),
            referees=tuple(
                clean(f"{r.findtext('firstname') or ''} {r.findtext('lastname') or ''}")
                for r in refs
            ),
        )
        if game.played and any(p != (0, 0) for p in partials):
            game = replace(game, partials=partials)
        games.append(game)
    return games


def parse_table(payload: bytes) -> list[Standing]:
    """Parse ``table.php`` output (may be empty, e.g. for play-off phases)."""
    root = _parse_root(payload, "table")
    rows = [
        Standing(
            position=_int(node.findtext("pos")),
            team=_team(node),
            games_played=_int(node.findtext("gp")),
            wins=_int(node.findtext("gw")),
            losses=_int(node.findtext("gl")),
            points_scored=_int(node.findtext("sp")),
            points_conceded=_int(node.findtext("sm")),
            points=_int(node.findtext("pt")),
        )
        for node in root.findall("team")
    ]
    return sorted(rows, key=lambda r: r.position)


def parse_phase_reference(text: str) -> int | None:
    """Extract a phase id from a plain number or a cbf.cz URL containing ``p=``."""
    text = text.strip()
    if text.isdigit():
        return int(text)
    match = re.search(r"[?&]p=(\d+)", text)
    return int(match.group(1)) if match else None


def default_season(today: date) -> int:
    """Season id for a date; seasons start in August (2026 = 2026/27)."""
    return today.year if today.month >= 8 else today.year - 1


# --------------------------------------------------------------------------
# Team view
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TeamView:
    """Team-centric view of a phase."""

    team_id: int
    data: PhaseData

    @property
    def games(self) -> list[Game]:
        """All games of the team, chronologically (unscheduled last)."""
        return sorted(
            (g for g in self.data.games if g.involves(self.team_id)),
            key=lambda g: g.sort_key,
        )

    @property
    def standing(self) -> Standing | None:
        """The team's table row."""
        return next((r for r in self.data.table if r.team.id == self.team_id), None)

    @property
    def played_games(self) -> list[Game]:
        """Played games, chronologically."""
        return [g for g in self.games if g.played]

    def next_game(self, now: datetime) -> Game | None:
        """The next game that has not started yet.

        Games whose time is unknown count until the end of their day. Past games
        without a result ("awaiting result") and unscheduled games are skipped.
        """
        today = now.astimezone(CBF_TZ).date()
        for game in self.games:
            if game.played or game.game_date is None:
                continue
            start = game.start
            if start is not None:
                if start > now:
                    return game
            elif game.game_date >= today:
                return game
        return None

    def next_transition(self, now: datetime) -> datetime | None:
        """When ``next_game`` changes without new data."""
        game = self.next_game(now)
        if game is None or game.game_date is None:
            return None
        if game.start is not None:
            return game.start
        return datetime.combine(
            game.game_date + timedelta(days=1), time.min, tzinfo=CBF_TZ
        )

    @property
    def last_game(self) -> Game | None:
        """The most recent game with a result."""
        played = self.played_games
        return played[-1] if played else None

    @property
    def games_remaining(self) -> int:
        """Games without a result."""
        return sum(1 for g in self.games if not g.played)

    @property
    def season_finished(self) -> bool:
        """All the team's games have a result."""
        games = self.games
        return bool(games) and all(g.played for g in games)

    @property
    def streak(self) -> str | None:
        """Current streak like ``W2`` or ``L3``."""
        outcomes = [g.won(self.team_id) for g in self.played_games]
        outcomes = [o for o in outcomes if o is not None]
        if not outcomes:
            return None
        last = outcomes[-1]
        count = 0
        for outcome in reversed(outcomes):
            if outcome != last:
                break
            count += 1
        return f"{'W' if last else 'L'}{count}"

    def head_to_head(self, opponent_id: int) -> dict[str, Any]:
        """Results against an opponent in this phase."""
        games = [
            g for g in self.played_games if g.opponent(self.team_id).id == opponent_id
        ]
        results = []
        wins = losses = 0
        for game in games:
            own, opp = game.score_for(self.team_id)
            won = game.won(self.team_id)
            wins += won is True
            losses += won is False
            results.append(
                {
                    "date": game.game_date.isoformat() if game.game_date else None,
                    "home": game.is_home(self.team_id),
                    "score": f"{own}:{opp}",
                    "outcome": None if won is None else ("win" if won else "loss"),
                }
            )
        return {"wins": wins, "losses": losses, "games": results}


# --------------------------------------------------------------------------
# HTTP client
# --------------------------------------------------------------------------


class CbfClient:
    """Async client of the CBF XML exports."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str = BASE_URL) -> None:
        """Initialise with an (injected) aiohttp session."""
        self._session = session
        self._base_url = base_url

    async def _get(self, script: str, params: dict[str, Any]) -> bytes:
        try:
            async with self._session.get(
                f"{self._base_url}{script}",
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                return await resp.read()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CbfConnectionError(f"Error fetching {script}: {err}") from err

    async def get_divisions(self, season: int) -> list[Division]:
        """Competitions of a season."""
        return parse_divisions(await self._get("divs.php", {"s": season}))

    async def get_schedule(self, phase_id: int) -> list[Game]:
        """Games of a phase."""
        return parse_schedule(await self._get("sched.php", {"p": phase_id}))

    async def get_table(self, phase_id: int) -> list[Standing]:
        """Standings of a phase."""
        return parse_table(await self._get("table.php", {"p": phase_id}))


def filter_divisions(
    divisions: Iterable[Division], category: str | None = None, search: str | None = None
) -> list[Division]:
    """Competitions with at least one phase, optionally filtered."""
    needle = (search or "").casefold().replace(" ", "")
    result = []
    for div in divisions:
        if not div.phases:
            continue
        if category and div.category != category:
            continue
        if needle and needle not in div.label.casefold().replace(" ", ""):
            continue
        result.append(div)
    return sorted(result, key=lambda d: (d.category.casefold(), d.name.casefold()))
