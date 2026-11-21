"""The CBF (Czech Basketball Federation) integration."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN
from .coordinator import CbfConfigEntry, CbfCoordinator, season_issue_id

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: CbfConfigEntry) -> bool:
    """Set up a followed team from a config entry."""
    coordinator = CbfCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    @callback
    def _on_update() -> None:
        coordinator.async_post_update()

    entry.async_on_unload(coordinator.async_add_listener(_on_update))
    entry.async_on_unload(coordinator.async_shutdown_transition)
    coordinator.async_post_update()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CbfConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: CbfConfigEntry) -> None:
    """Clean up repair issues of a removed entry."""
    ir.async_delete_issue(hass, DOMAIN, season_issue_id(entry.entry_id))
