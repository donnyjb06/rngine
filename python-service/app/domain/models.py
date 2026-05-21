from .constrained_types import Percentage
from typing import Literal, Optional
from pydantic import BaseModel


class ProbabilityEntity(BaseModel):
    name: str


class RawProbabilityEntity(ProbabilityEntity):
    weight: Optional[float] = None
    probability: Optional[Percentage] = None


class NormalizedProbabilityEntity(ProbabilityEntity):
    probability: Percentage


class RawLootItem(RawProbabilityEntity):
    value: Optional[int] = None


class NormalizedLootItem(NormalizedProbabilityEntity):
    value: Optional[int] = None


class RawRarity(RawProbabilityEntity):
    items: list[RawLootItem]


class NormalizedRarity(NormalizedProbabilityEntity):
    items: list[NormalizedLootItem]


class BaseSimulationConfig(BaseModel):
    simulation_count: int
    pulls_per_simulation: int
    duplicate_mode: Literal["allow_duplicates", "duplicate_currency", "hard_prevention"]
    seed: int | None
    item_selection_mode: Literal["item_probability", "equal_chance"]


class RawSimulationConfig(BaseSimulationConfig):
    rarities: list[RawRarity]
    probability_mode: Literal["percentage", "weight"]


class NormalizedSimulationConfig(BaseSimulationConfig):
    rarities: list[NormalizedRarity]
