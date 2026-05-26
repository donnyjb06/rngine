from dataclasses import dataclass, field
from typing import TypedDict
from app.domain.models import NormalizedProbabilityEntity


class EndpointData(TypedDict):
    entities: list[NormalizedProbabilityEntity]
    percentages: list[float]


class Endpoints(TypedDict):
    rarities: EndpointData
    items: dict[str, EndpointData]

@dataclass
class SimulationState:
    endpoints: Endpoints
    eligible_items_by_rarity: dict[str, list[str]]
    current_total_pulls: int = 0
    pulled_items: set[str] = field(default_factory=set)
    pulled_rarities: set[str] = field(default_factory=set)


@dataclass
class ProbabilityEntityStats:
    expected_probability: dict[str, float]
    pull_counts: dict[str, int]
    currency_amounts: dict[str, int] | None
    duplicate_amounts: dict[str, int] | None
    average_pulls_until_entity: dict[str, float] | None
    observed_probability: dict[str, float] = field(default_factory=dict)


@dataclass
class RarityStats:
    average_pulls_until_completion: dict[str, float] = field(default_factory=dict)


@dataclass
class GlobalStats:
    total_duplicates: int | None
    total_currency: int | None
    mean_currency: float | None
    median_currency: float | None
    currency_stdev: float | None
    average_duplicate_count: float | None
    total_pulls: int = 0


class SimulationStats(TypedDict):
    global_stats: GlobalStats
    rarity_stats: RarityStats
    item_stats: ProbabilityEntityStats


@dataclass
class SimulationAggregationStats:
    mean_currency_per_simulation: list[float] = field(default_factory=list)
    total_currency_per_simulation: list[float] = field(default_factory=list)
    duplicate_amounts_per_simulation: list[int] = field(default_factory=list)
