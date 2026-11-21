"""Constants for the CBF integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Final

DOMAIN: Final = "cbf"
LOGGER = logging.getLogger(__package__)

CONF_SEASON: Final = "season"
CONF_CATEGORY: Final = "category"
CONF_SEARCH: Final = "search"
CONF_PHASE_REF: Final = "phase_ref"
CONF_DIVISION_ID: Final = "division_id"
CONF_DIVISION_NAME: Final = "division_name"
CONF_PHASE_ID: Final = "phase_id"
CONF_PHASE_NAME: Final = "phase_name"
CONF_TEAM_ID: Final = "team_id"
CONF_TEAM_NAME: Final = "team_name"
CONF_SCAN_INTERVAL_HOURS: Final = "scan_interval_hours"

DEFAULT_SCAN_INTERVAL_HOURS: Final = 3
MIN_SCAN_INTERVAL_HOURS: Final = 1
MAX_SCAN_INTERVAL_HOURS: Final = 24
DEFAULT_SCAN_INTERVAL: Final = timedelta(hours=DEFAULT_SCAN_INTERVAL_HOURS)

MANUFACTURER: Final = "Česká basketbalová federace"
WEBSITE: Final = "https://cz.basketball"
