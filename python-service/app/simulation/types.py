from dataclasses import dataclass, field
from typing import TypeVar, TypedDict
from app.domain.models import (
    NormalizedLootItem,
    NormalizedProbabilityEntity,
    NormalizedRarity,
)

T = TypeVar("T", bound=NormalizedProbabilityEntity)


class EndpointData[T](TypedDict):
    entities: list[T]
    percentages: list[float]


class Endpoints(TypedDict):
    rarities: EndpointData[NormalizedRarity]
    items: dict[str, EndpointData[NormalizedLootItem]]


@dataclass
class PulledEntities:
    item: NormalizedLootItem
    rarity: NormalizedRarity


@dataclass
class SimulationState:
    endpoints: Endpoints
    eligible_items_by_rarity: dict[str, list[NormalizedLootItem]]
    current_total_pulls: int = 0
    pulled_items: list[NormalizedLootItem] = field(default_factory=list)
    pulled_rarities: list[NormalizedRarity] = field(default_factory=list)


@dataclass
class ProbabilityEntityStats:
    pull_counts: dict[str, int]
    currency_amounts: dict[str, int]


@dataclass
class ItemStats(ProbabilityEntityStats):
    duplicate_amounts: dict[str, int]


@dataclass
class SimulationStats:
    rarity_stats: ProbabilityEntityStats
    item_stats: ItemStats
    total_currency: int = 0
    total_duplicates: int = 0


@dataclass
class AggregationProbabilityEntityStats:
    pulls_until_entity: dict[str, list[int]]


@dataclass
class AggregationRarityStats(AggregationProbabilityEntityStats):
    pulls_until_completion: dict[str, list[int]]


@dataclass
class SimulationAggregationStats:
    item_stats: AggregationProbabilityEntityStats
    rarity_stats: AggregationRarityStats
    total_currency_per_simulation: list[float] = field(default_factory=list)
    duplicate_amounts_per_simulation: list[int] = field(default_factory=list)


@dataclass
class BatchProbabilityEntityStats:
    expected_probability: dict[str, float]
    pull_counts: dict[str, int]
    currency_amounts: dict[str, int]
    average_pulls_until_entity: dict[str, float]
    observed_probability: dict[str, float] = field(default_factory=dict)


@dataclass
class BatchItemStats(BatchProbabilityEntityStats):
    duplicate_amounts: dict[str, int] = field(default_factory=dict)


@dataclass
class BatchRarityStats(BatchProbabilityEntityStats):
    average_pulls_until_completion: dict[str, float] = field(default_factory=dict)


@dataclass
class GlobalStats:
    mean_currency: float
    median_currency: float
    currency_stdev: float
    average_duplicate_count: float
    total_pulls: int = 0
    total_duplicates: int = 0
    total_currency: int = 0


@dataclass
class SimulationBatchStats:
    global_stats: GlobalStats
    rarity_stats: BatchRarityStats
    item_stats: BatchItemStats


@dataclass
class PullResult:
    rarity: NormalizedRarity
    item: NormalizedLootItem
    is_duplicate: bool
    currency_awarded: int
    is_rarity_first_pull: bool
    is_item_first_pull: bool
    is_rarity_complete: bool


type CurrencyMap = dict[str, int]


class SimulationTrackingStats(TypedDict):
    simulation: SimulationStats
    aggregation: SimulationAggregationStats

class DuplicationConfig(TypedDict):
    is_hard_prevention: bool
    are_duplicate_possible: bool
