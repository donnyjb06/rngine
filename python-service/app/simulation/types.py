from typing import TypedDict
from random import Random


class EndpointData(TypedDict):
    index: set[str]
    percentages: list[float]


class Endpoints(TypedDict):
    rarities: EndpointData
    items: dict[str, EndpointData]


class SimulationState(TypedDict):
    rng: Random
    pulled_items: set[str]
    pulled_rarities: set[str]
    eligible_items_by_rarity: dict[str, list[str]]
    endpoints: Endpoints
    current_total_pulls: int


class ProbabilityEntityStats(TypedDict):
    expected_probability: dict[str, float]
    pull_counts: dict[str, int]
    currency_amounts: dict[str, int] | None
    duplicate_amounts: dict[str, int] | None
    average_pulls_until_entity: dict[str, float] | None
    observed_probability: dict[str, float]


class RarityStats(ProbabilityEntityStats):
    average_pulls_until_completion: dict[str, float]


class GlobalStats(TypedDict):
    total_pulls: int
    total_duplicates: int | None
    total_currency: int | None
    mean_currency: float | None
    median_currency: float | None
    currency_stdev: float | None
    average_duplicate_count: float | None


class SimulationStats(TypedDict):
    global_stats: GlobalStats
    rarity_stats: RarityStats
    item_stats: ProbabilityEntityStats


class SimulationAggregationStats(TypedDict):
    mean_currency_per_simulation: list[float]
    total_currency_per_simulation: list[float]
    duplicate_amounts_per_simulation: list[int]
