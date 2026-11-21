"""Calendar of a followed team's games."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import CBF_TZ, GAME_DURATION, Game
from .coordinator import CbfConfigEntry, CbfCoordinator
from .entity import CbfEntity

PARALLEL_UPDATES = 0

_TEXTS = {
    "en": {
        "round": "Round",
        "result": "Result",
        "time_tbc": "Tip-off time not confirmed yet",
        "referees": "Referees",
        "tbc": "time TBC",
    },
    "cs": {
        "round": "Kolo",
        "result": "Výsledek",
        "time_tbc": "Čas utkání zatím není potvrzen",
        "referees": "Rozhodčí",
        "tbc": "čas neurčen",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CbfConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the CBF calendar."""
    async_add_entities([CbfCalendar(entry.runtime_data)])


class CbfCalendar(CbfEntity, CalendarEntity):
    """Calendar with all games of the team in the followed phase."""

    _attr_name = None  # the device (team) name

    def __init__(self, coordinator: CbfCoordinator) -> None:
        """Initialise the calendar."""
        super().__init__(coordinator, "calendar")

    def _texts(self) -> dict[str, str]:
        lang = (self.hass.config.language or "en").split("-")[0]
        return _TEXTS.get(lang, _TEXTS["en"])

    def _event(self, game: Game) -> CalendarEvent | None:
        if game.game_date is None:
            return None
        team_id = self.coordinator.team_id
        texts = self._texts()
        summary = f"{game.home.name} – {game.away.name}"
        lines = [f"{texts['round']}: {game.round}"] if game.round else []
        if game.played:
            own, opp = game.score_for(team_id)
            summary += f" {game.home_score}:{game.away_score}"
            lines.append(f"{texts['result']}: {own}:{opp}")
        if game.referees:
            lines.append(f"{texts['referees']}: {', '.join(game.referees)}")
        start = game.start
        if start is None:
            if not game.played:
                summary += f" ({texts['tbc']})"
                lines.append(texts["time_tbc"])
            return CalendarEvent(
                start=game.game_date,
                end=game.game_date + timedelta(days=1),
                summary=summary,
                description="\n".join(lines),
                location=game.location or None,
                uid=str(game.id),
            )
        return CalendarEvent(
            start=start,
            end=start + GAME_DURATION,
            summary=summary,
            description="\n".join(lines),
            location=game.location or None,
            uid=str(game.id),
        )

    def _events(self) -> list[CalendarEvent]:
        events = [self._event(game) for game in self.coordinator.view.games]
        return [event for event in events if event is not None]

    @property
    def event(self) -> CalendarEvent | None:
        """The current or next upcoming game."""
        now = dt_util.now()
        today = now.astimezone(CBF_TZ).date()
        for event in self._events():
            if isinstance(event.end, datetime):
                if event.end > now:
                    return event
            elif event.end > today:
                return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Games between the given dates."""
        return [
            event
            for event in self._events()
            if event.start_datetime_local < end_date
            and event.end_datetime_local > start_date
        ]
