"""Tests of the config flow, setup and entities."""

from __future__ import annotations

from datetime import datetime

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from homeassistant import config_entries
from homeassistant.components.calendar import DOMAIN as CALENDAR_DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er

from custom_components.cbf.api import CBF_TZ
from custom_components.cbf.const import (
    CONF_DIVISION_ID,
    CONF_DIVISION_NAME,
    CONF_PHASE_ID,
    CONF_PHASE_NAME,
    CONF_SCAN_INTERVAL_HOURS,
    CONF_SEASON,
    CONF_TEAM_ID,
    CONF_TEAM_NAME,
    DOMAIN,
)

from .conftest import PHASE_ID, TEAM_ID, load

BASE = "https://www.cbf.cz/xml/"
NOW = datetime(2026, 11, 21, 12, 0, tzinfo=CBF_TZ)


@pytest.fixture
def cbf_mock(aioclient_mock: AiohttpClientMocker) -> AiohttpClientMocker:
    """Mock the CBF endpoints."""
    aioclient_mock.get(f"{BASE}divs.php", content=load("divs_2026.xml"))
    aioclient_mock.get(f"{BASE}sched.php", content=load("sched_10469.xml"))
    aioclient_mock.get(f"{BASE}table.php", content=load("table_10469.xml"))
    return aioclient_mock


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="TJ ÚVN – 2.třída B",
        unique_id=f"{PHASE_ID}_{TEAM_ID}",
        data={
            CONF_SEASON: 2026,
            "category": "muži",
            CONF_DIVISION_ID: 5382,
            CONF_DIVISION_NAME: "2.třída B",
            CONF_PHASE_ID: PHASE_ID,
            CONF_PHASE_NAME: "Základní fáze",
            CONF_TEAM_ID: TEAM_ID,
            CONF_TEAM_NAME: "TJ ÚVN",
        },
    )


async def test_config_flow_search(
    hass: HomeAssistant, cbf_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    """Search narrows to one category -> competition -> (single phase) -> team."""
    freezer.move_to(NOW)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SEASON: 2026, "search": "2.třída", "phase_ref": ""}
    )
    assert result["step_id"] == "competition"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"competition": "5382"}
    )
    assert result["step_id"] == "team"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"team": str(TEAM_ID)}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "TJ ÚVN – 2.třída B"
    assert result["data"][CONF_PHASE_ID] == PHASE_ID
    assert result["result"].unique_id == f"{PHASE_ID}_{TEAM_ID}"


async def test_config_flow_category_and_phase_ref(
    hass: HomeAssistant, cbf_mock: AiohttpClientMocker
) -> None:
    """No search -> category step; pasted URL jumps to team."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SEASON: 2026, "search": "", "phase_ref": ""}
    )
    assert result["step_id"] == "category"

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SEASON: 2026, "phase_ref": "xyz"}
    )
    assert result["errors"] == {"phase_ref": "invalid_phase"}
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SEASON: 2026, "phase_ref": f"https://www.cbf.cz/xml/sched.php?p={PHASE_ID}"},
    )
    assert result["step_id"] == "team"


async def test_config_flow_already_configured(
    hass: HomeAssistant, cbf_mock: AiohttpClientMocker
) -> None:
    """The same team in the same phase can be added only once."""
    _entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SEASON: 2026, "phase_ref": str(PHASE_ID)}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"team": str(TEAM_ID)}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_config_flow_cannot_connect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Connection errors are shown on the first step."""
    aioclient_mock.get(f"{BASE}divs.php", status=503)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SEASON: 2026}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_setup_and_entities(
    hass: HomeAssistant, cbf_mock: AiohttpClientMocker, freezer: FrozenDateTimeFactory
) -> None:
    """Entities reflect the fixture data and switch at tip-off."""
    freezer.move_to(datetime(2026, 11, 26, 19, 0, tzinfo=CBF_TZ))
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED

    registry = er.async_get(hass)
    ids = {
        e.translation_key or e.original_name: e.entity_id
        for e in er.async_entries_for_config_entry(registry, entry.entry_id)
    }

    next_game = hass.states.get(ids["next_game"])
    assert next_game.state == "2026-11-26T18:40:00+00:00"
    assert next_game.attributes["opponent"] == "Sokol Dolní Počernice C"
    assert next_game.attributes["home"] is False
    assert hass.states.get(ids["next_opponent"]).state == "Sokol Dolní Počernice C"
    assert hass.states.get(ids["last_game"]).state == "54:83"
    assert hass.states.get(ids["last_game_outcome"]).state == "loss"
    position = hass.states.get(ids["position"])
    assert position.state == "7"
    assert len(position.attributes["table"]) == 12
    assert hass.states.get(ids["points"]).state == "9"
    assert hass.states.get(ids["games_remaining"]).state == "15"
    assert hass.states.get(ids["streak"]).state == "L2"

    calendar = hass.states.get("calendar.tj_uvn")
    assert calendar is not None
    assert calendar.attributes["message"].startswith("Sokol Dolní Počernice C – TJ ÚVN")

    requests = cbf_mock.call_count
    # tip-off of the next game: sensors move on without fetching
    freezer.move_to(datetime(2026, 11, 26, 19, 41, tzinfo=CBF_TZ))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(ids["next_opponent"]).state == "Fenix Modřany B"
    assert cbf_mock.call_count == requests

    events = await hass.services.async_call(
        CALENDAR_DOMAIN,
        "get_events",
        {
            "entity_id": "calendar.tj_uvn",
            "start_date_time": "2027-01-01T00:00:00+01:00",
            "end_date_time": "2027-01-31T00:00:00+01:00",
        },
        blocking=True,
        return_response=True,
    )
    jan = events["calendar.tj_uvn"]["events"]
    assert len(jan) == 3
    assert jan[0]["start"] == "2027-01-11"  # all-day, time not confirmed

    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_table_fetched_only_on_new_results(
    hass: HomeAssistant, cbf_mock: AiohttpClientMocker
) -> None:
    """A refresh without new results only fetches the schedule."""
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    before = cbf_mock.call_count
    await entry.runtime_data.async_refresh()
    assert cbf_mock.call_count == before + 1


async def test_setup_retry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Setup is retried when CBF is down."""
    aioclient_mock.get(f"{BASE}sched.php", status=500)
    entry = _entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_options_and_reconfigure(
    hass: HomeAssistant, cbf_mock: AiohttpClientMocker
) -> None:
    """Options set the interval; reconfigure keeps the entry."""
    entry = _entry()
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL_HOURS: 6}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval.total_seconds() == 6 * 3600

    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SEASON: 2026, "phase_ref": str(PHASE_ID)}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"team": "7814"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_TEAM_NAME] == "TJ Slavoj OS A"
    assert entry.unique_id == f"{PHASE_ID}_7814"
