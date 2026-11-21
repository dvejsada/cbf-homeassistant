"""Config flow for the CBF integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
from homeassistant.util import dt as dt_util

from .api import (
    CbfClient,
    CbfConnectionError,
    CbfError,
    Division,
    Phase,
    PhaseData,
    default_season,
    filter_divisions,
    parse_phase_reference,
)
from .const import (
    CONF_CATEGORY,
    CONF_DIVISION_ID,
    CONF_DIVISION_NAME,
    CONF_PHASE_ID,
    CONF_PHASE_NAME,
    CONF_PHASE_REF,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_SEARCH,
    CONF_SEASON,
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    DEFAULT_SCAN_INTERVAL_HOURS,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL_HOURS,
    MIN_SCAN_INTERVAL_HOURS,
)
from .coordinator import CbfConfigEntry

CONF_COMPETITION = "competition"
CONF_PHASE = "phase"
CONF_TEAM = "team"


def _select(options: list[SelectOptionDict]) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=options, mode=SelectSelectorMode.DROPDOWN, sort=False
        )
    )


class CbfConfigFlow(ConfigFlow, domain=DOMAIN):
    """Pick a season, competition, phase and team."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialise the flow."""
        self._season: int = 0
        self._search: str = ""
        self._divisions: list[Division] = []
        self._category: str | None = None
        self._division: Division | None = None
        self._phase: Phase | None = None
        self._phase_data: PhaseData | None = None

    @property
    def _client(self) -> CbfClient:
        return CbfClient(async_get_clientsession(self.hass))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: CbfConfigEntry) -> CbfOptionsFlow:
        """Return the options flow."""
        return CbfOptionsFlow()

    # -- step 1: season / search / direct phase -------------------------------

    def _start_schema(self, defaults: dict[str, Any]) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    CONF_SEASON, default=defaults.get(CONF_SEASON)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=2000, max=2100, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Optional(
                    CONF_SEARCH, default=defaults.get(CONF_SEARCH, "")
                ): TextSelector(),
                vol.Optional(CONF_PHASE_REF, default=""): TextSelector(),
            }
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Start: choose a season, optionally search or paste a phase."""
        return await self._async_start("user", user_input)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Re-point the entry to another phase (e.g. a new season)."""
        return await self._async_start("reconfigure", user_input)

    async def _async_start(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        defaults: dict[str, Any] = {CONF_SEASON: default_season(dt_util.now().date())}
        if step_id == "reconfigure":
            entry = self._get_reconfigure_entry()
            defaults[CONF_SEARCH] = entry.data.get(CONF_DIVISION_NAME, "")

        if user_input is not None:
            defaults = user_input
            self._season = int(user_input[CONF_SEASON])
            self._search = (user_input.get(CONF_SEARCH) or "").strip()
            phase_ref = (user_input.get(CONF_PHASE_REF) or "").strip()
            try:
                self._divisions = await self._client.get_divisions(self._season)
            except CbfConnectionError:
                errors["base"] = "cannot_connect"
            except CbfError:
                LOGGER.exception("Unexpected data from CBF")
                errors["base"] = "invalid_data"
            else:
                if phase_ref:
                    result = await self._async_use_phase_ref(phase_ref, errors)
                    if result is not None:
                        return result
                else:
                    candidates = filter_divisions(self._divisions, search=self._search)
                    categories = sorted({d.category for d in candidates})
                    if not categories:
                        errors["base"] = "no_competitions"
                    elif len(categories) == 1:
                        self._category = categories[0]
                        return await self.async_step_competition()
                    else:
                        return await self.async_step_category()

        return self.async_show_form(
            step_id=step_id,
            data_schema=self._start_schema(defaults),
            errors=errors,
        )

    async def _async_use_phase_ref(
        self, phase_ref: str, errors: dict[str, str]
    ) -> ConfigFlowResult | None:
        phase_id = parse_phase_reference(phase_ref)
        if phase_id is None:
            errors[CONF_PHASE_REF] = "invalid_phase"
            return None
        for division in self._divisions:
            for phase in division.phases:
                if phase.id == phase_id:
                    self._division, self._phase = division, phase
                    return await self.async_step_team()
        errors[CONF_PHASE_REF] = "phase_not_found"
        return None

    # -- step 2: category ------------------------------------------------------

    async def async_step_category(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose a category (men, women, U13, ...)."""
        if user_input is not None:
            self._category = user_input[CONF_CATEGORY]
            return await self.async_step_competition()
        candidates = filter_divisions(self._divisions, search=self._search)
        counts: dict[str, int] = {}
        for division in candidates:
            counts[division.category] = counts.get(division.category, 0) + 1
        options = [
            SelectOptionDict(value=cat, label=f"{cat} ({count})")
            for cat, count in sorted(counts.items(), key=lambda i: i[0].casefold())
        ]
        return self.async_show_form(
            step_id="category",
            data_schema=vol.Schema({vol.Required(CONF_CATEGORY): _select(options)}),
        )

    # -- step 3: competition ---------------------------------------------------

    async def async_step_competition(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose a competition."""
        candidates = filter_divisions(
            self._divisions, category=self._category, search=self._search
        )
        if user_input is not None:
            division_id = int(user_input[CONF_COMPETITION])
            self._division = next(d for d in candidates if d.id == division_id)
            if len(self._division.phases) == 1:
                self._phase = self._division.phases[0]
                return await self.async_step_team()
            return await self.async_step_phase()
        options = [SelectOptionDict(value=str(d.id), label=d.label) for d in candidates]
        return self.async_show_form(
            step_id="competition",
            data_schema=vol.Schema({vol.Required(CONF_COMPETITION): _select(options)}),
            description_placeholders={
                "category": self._category or "",
                "count": str(len(candidates)),
            },
        )

    # -- step 4: phase ---------------------------------------------------------

    async def async_step_phase(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose a phase of the competition."""
        assert self._division is not None
        if user_input is not None:
            phase_id = int(user_input[CONF_PHASE])
            self._phase = next(p for p in self._division.phases if p.id == phase_id)
            return await self.async_step_team()
        options = [
            SelectOptionDict(value=str(p.id), label=p.name)
            for p in self._division.phases
        ]
        return self.async_show_form(
            step_id="phase",
            data_schema=vol.Schema({vol.Required(CONF_PHASE): _select(options)}),
            description_placeholders={"competition": self._division.label},
        )

    # -- step 5: team ----------------------------------------------------------

    async def async_step_team(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose the team to follow."""
        assert self._division is not None and self._phase is not None
        if self._phase_data is None:
            try:
                games = await self._client.get_schedule(self._phase.id)
                table = await self._client.get_table(self._phase.id)
            except CbfConnectionError:
                return self.async_abort(reason="cannot_connect")
            except CbfError:
                LOGGER.exception("Unexpected data from CBF")
                return self.async_abort(reason="invalid_data")
            self._phase_data = PhaseData(games=tuple(games), table=tuple(table))

        teams = self._phase_data.teams()
        if not teams:
            return self.async_abort(reason="no_teams")

        if user_input is not None:
            team_id = int(user_input[CONF_TEAM])
            team = next(t for t in teams if t.id == team_id)
            return await self._async_finish(team.id, team.name)

        options = [SelectOptionDict(value=str(t.id), label=t.name) for t in teams]
        return self.async_show_form(
            step_id="team",
            data_schema=vol.Schema({vol.Required(CONF_TEAM): _select(options)}),
            description_placeholders={
                "competition": self._division.label,
                "phase": self._phase.name,
            },
        )

    async def _async_finish(self, team_id: int, team_name: str) -> ConfigFlowResult:
        assert self._division is not None and self._phase is not None
        data = {
            CONF_SEASON: self._season,
            CONF_CATEGORY: self._division.category,
            CONF_DIVISION_ID: self._division.id,
            CONF_DIVISION_NAME: self._division.name,
            CONF_PHASE_ID: self._phase.id,
            CONF_PHASE_NAME: self._phase.name,
            CONF_TEAM_ID: team_id,
            CONF_TEAM_NAME: team_name,
        }
        title = f"{team_name} – {self._division.name}"
        unique_id = f"{self._phase.id}_{team_id}"

        if self.source == SOURCE_RECONFIGURE:
            entry = self._get_reconfigure_entry()
            if unique_id != entry.unique_id:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
            return self.async_update_reload_and_abort(
                entry, unique_id=unique_id, title=title, data=data
            )

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=title, data=data)


class CbfOptionsFlow(OptionsFlowWithReload):
    """Polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_SCAN_INTERVAL_HOURS: int(user_input[CONF_SCAN_INTERVAL_HOURS])}
            )
        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL_HOURS, DEFAULT_SCAN_INTERVAL_HOURS
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL_HOURS, default=current
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL_HOURS,
                            max=MAX_SCAN_INTERVAL_HOURS,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="h",
                        )
                    )
                }
            ),
        )
