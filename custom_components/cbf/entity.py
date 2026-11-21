"""Base entity for the CBF integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_DIVISION_NAME,
    CONF_PHASE_ID,
    CONF_TEAM_NAME,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import CbfCoordinator


class CbfEntity(CoordinatorEntity[CbfCoordinator]):
    """An entity belonging to a followed team."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CbfCoordinator, key: str) -> None:
        """Initialise the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        # Unique ids are based on the entry, so history survives a reconfigure
        # to a new phase / season.
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data[CONF_TEAM_NAME],
            manufacturer=MANUFACTURER,
            model=entry.data[CONF_DIVISION_NAME],
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=(
                f"https://www.cbf.cz/xml/sched.php?p={entry.data[CONF_PHASE_ID]}"
            ),
        )
