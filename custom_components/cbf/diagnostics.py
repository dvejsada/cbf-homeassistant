"""Diagnostics for the CBF integration."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .coordinator import CbfConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CbfConfigEntry
) -> dict[str, Any]:
    """Return diagnostics (referee names are left out)."""
    coordinator = entry.runtime_data
    view = coordinator.view
    return {
        "entry": {"data": dict(entry.data), "options": dict(entry.options)},
        "last_success": coordinator.last_success,
        "update_interval": str(coordinator.update_interval),
        "games_in_phase": len(coordinator.data.games),
        "table_rows": len(coordinator.data.table),
        "team_games": [
            {
                "id": g.id,
                "round": g.round,
                "date": g.game_date,
                "time": g.game_time,
                "home": g.home.name,
                "away": g.away.name,
                "played": g.played,
                "score": f"{g.home_score}:{g.away_score}",
            }
            for g in view.games
        ],
    }
