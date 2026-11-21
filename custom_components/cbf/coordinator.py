"""Data update coordinator for the CBF integration."""

from __future__ import annotations

from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import CbfClient, CbfError, PhaseData, TeamView
from .const import (
    CONF_DIVISION_NAME,
    CONF_PHASE_ID,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    LOGGER,
)

type CbfConfigEntry = ConfigEntry[CbfCoordinator]


def season_issue_id(entry_id: str) -> str:
    """Repair issue id for a finished season."""
    return f"season_finished_{entry_id}"


class CbfCoordinator(DataUpdateCoordinator[PhaseData]):
    """Fetches the schedule (and, when results change, the table) of one phase."""

    config_entry: CbfConfigEntry

    def __init__(self, hass: HomeAssistant, entry: CbfConfigEntry) -> None:
        """Initialise the coordinator."""
        hours = entry.options.get(CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS)
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN} {entry.title}",
            update_interval=timedelta(hours=hours),
        )
        self.client = CbfClient(async_get_clientsession(hass))
        self.phase_id: int = entry.data[CONF_PHASE_ID]
        self.team_id: int = entry.data[CONF_TEAM_ID]
        self.last_success: datetime | None = None
        self._unsub_transition: CALLBACK_TYPE | None = None

    @property
    def view(self) -> TeamView:
        """Team-centric view of the current data."""
        return TeamView(self.team_id, self.data)

    async def _async_update_data(self) -> PhaseData:
        try:
            games = await self.client.get_schedule(self.phase_id)
            previous = self.data
            new = PhaseData(games=tuple(games))
            if (
                previous is None
                or not previous.table
                or previous.results_signature != new.results_signature
            ):
                table = await self.client.get_table(self.phase_id)
            else:
                table = list(previous.table)
        except CbfError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        self.last_success = dt_util.utcnow()
        return PhaseData(games=tuple(games), table=tuple(table))

    @callback
    def async_post_update(self) -> None:
        """Schedule time based refresh and maintain repair issues."""
        if self.data is None:
            return
        self._schedule_transition()
        self._update_season_issue()

    @callback
    def _schedule_transition(self) -> None:
        """Refresh entities (without fetching) when the next game tips off."""
        if self._unsub_transition:
            self._unsub_transition()
            self._unsub_transition = None
        when = self.view.next_transition(dt_util.now())
        if when is None:
            return

        @callback
        def _fire(_now: datetime) -> None:
            self._unsub_transition = None
            self.async_update_listeners()
            self._schedule_transition()

        self._unsub_transition = async_track_point_in_time(self.hass, _fire, when)

    @callback
    def _update_season_issue(self) -> None:
        issue_id = season_issue_id(self.config_entry.entry_id)
        if self.view.season_finished:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="season_finished",
                translation_placeholders={
                    "team": self.config_entry.data[CONF_TEAM_NAME],
                    "division": self.config_entry.data[CONF_DIVISION_NAME],
                },
            )
        else:
            ir.async_delete_issue(self.hass, DOMAIN, issue_id)

    @callback
    def async_shutdown_transition(self) -> None:
        """Cancel the scheduled transition."""
        if self._unsub_transition:
            self._unsub_transition()
            self._unsub_transition = None
