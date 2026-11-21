"""Sensors for the CBF integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .api import Game, TeamView
from .coordinator import CbfConfigEntry, CbfCoordinator
from .entity import CbfEntity

PARALLEL_UPDATES = 0


def _game_attrs(view: TeamView, game: Game | None) -> dict[str, Any]:
    if game is None:
        return {}
    opponent = game.opponent(view.team_id)
    return {
        "game_id": game.id,
        "round": game.round,
        "date": game.game_date.isoformat() if game.game_date else None,
        "time_confirmed": game.time_known,
        "opponent": opponent.name,
        "opponent_id": opponent.id,
        "home": game.is_home(view.team_id),
        "venue": game.venue,
        "city": game.city,
    }


def _next_game_attrs(view: TeamView, now: datetime) -> dict[str, Any]:
    game = view.next_game(now)
    if game is None:
        return {}
    return {
        **_game_attrs(view, game),
        "head_to_head": view.head_to_head(game.opponent(view.team_id).id),
    }


def _next_game_value(view: TeamView, now: datetime) -> datetime | None:
    game = view.next_game(now)
    return game.start if game else None


def _next_opponent(view: TeamView, now: datetime) -> str | None:
    game = view.next_game(now)
    return game.opponent(view.team_id).name if game else None


def _next_opponent_attrs(view: TeamView, now: datetime) -> dict[str, Any]:
    game = view.next_game(now)
    if game is None:
        return {}
    return {"home": game.is_home(view.team_id)}


def _last_score(view: TeamView, _now: datetime) -> str | None:
    game = view.last_game
    if game is None:
        return None
    own, opp = game.score_for(view.team_id)
    return f"{own}:{opp}"


def _last_game_attrs(view: TeamView, _now: datetime) -> dict[str, Any]:
    game = view.last_game
    if game is None:
        return {}
    won = game.won(view.team_id)
    return {
        **_game_attrs(view, game),
        "outcome": None if won is None else ("win" if won else "loss"),
        "periods": [f"{a}:{b}" for a, b in game.quarters_for(view.team_id)],
    }


def _last_outcome(view: TeamView, _now: datetime) -> str | None:
    game = view.last_game
    if game is None:
        return None
    won = game.won(view.team_id)
    if won is None:
        return "draw"
    return "win" if won else "loss"


def _position_attrs(view: TeamView, _now: datetime) -> dict[str, Any]:
    row = view.standing
    attrs: dict[str, Any] = {"table": [r.as_dict() for r in view.data.table]}
    if row is not None:
        attrs |= {
            "games_played": row.games_played,
            "wins": row.wins,
            "losses": row.losses,
            "points_scored": row.points_scored,
            "points_conceded": row.points_conceded,
            "point_difference": row.point_difference,
            "points": row.points,
            "teams": len(view.data.table),
        }
    return attrs


@dataclass(frozen=True, kw_only=True)
class CbfSensorEntityDescription(SensorEntityDescription):
    """Describes a CBF sensor."""

    value_fn: Callable[[TeamView, datetime], StateType | datetime]
    attrs_fn: Callable[[TeamView, datetime], dict[str, Any]] | None = None


SENSORS: tuple[CbfSensorEntityDescription, ...] = (
    CbfSensorEntityDescription(
        key="next_game",
        translation_key="next_game",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_next_game_value,
        attrs_fn=_next_game_attrs,
    ),
    CbfSensorEntityDescription(
        key="next_opponent",
        translation_key="next_opponent",
        value_fn=_next_opponent,
        attrs_fn=_next_opponent_attrs,
    ),
    CbfSensorEntityDescription(
        key="last_game",
        translation_key="last_game",
        value_fn=_last_score,
        attrs_fn=_last_game_attrs,
    ),
    CbfSensorEntityDescription(
        key="last_game_outcome",
        translation_key="last_game_outcome",
        device_class=SensorDeviceClass.ENUM,
        options=["win", "loss", "draw"],
        value_fn=_last_outcome,
    ),
    CbfSensorEntityDescription(
        key="position",
        translation_key="position",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda view, _now: view.standing.position if view.standing else None,
        attrs_fn=_position_attrs,
    ),
    CbfSensorEntityDescription(
        key="points",
        translation_key="points",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda view, _now: view.standing.points if view.standing else None,
    ),
    CbfSensorEntityDescription(
        key="games_remaining",
        translation_key="games_remaining",
        value_fn=lambda view, _now: view.games_remaining,
    ),
    CbfSensorEntityDescription(
        key="streak",
        translation_key="streak",
        value_fn=lambda view, _now: view.streak,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CbfConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up CBF sensors."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [
        CbfSensor(coordinator, description) for description in SENSORS
    ]
    entities.append(CbfLastUpdateSensor(coordinator))
    async_add_entities(entities)


class CbfSensor(CbfEntity, SensorEntity):
    """A CBF sensor."""

    entity_description: CbfSensorEntityDescription
    # Bulky / personal attributes are kept out of the recorder.
    _unrecorded_attributes = frozenset({"table", "head_to_head", "periods"})

    def __init__(
        self, coordinator: CbfCoordinator, description: CbfSensorEntityDescription
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> StateType | datetime:
        """Return the state."""
        return self.entity_description.value_fn(self.coordinator.view, dt_util.now())

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes."""
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.view, dt_util.now())


class CbfLastUpdateSensor(CbfEntity, SensorEntity):
    """Time of the last successful fetch."""

    _attr_translation_key = "last_update"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: CbfCoordinator) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, "last_update")

    @property
    def native_value(self) -> datetime | None:
        """Return the state."""
        return self.coordinator.last_success

    @property
    def available(self) -> bool:
        """Stay available to show when data was last fetched."""
        return self.coordinator.last_success is not None
