from typing import Sequence

from app.domain.models import (
    NormalizedLootItem,
    NormalizedProbabilityEntity,
    NormalizedRarity,
)
from app.simulation.types import (
    AggregationProbabilityEntityStats,
    AggregationRarityStats,
    PullResult,
    SimulationAggregationStats,
)


def initialize_empty_lists(
    entities: Sequence[NormalizedProbabilityEntity],
) -> dict[str, list[int]]:
    return {entity.name: [] for entity in entities}


def create_item_aggregation_stats(
    items: list[NormalizedLootItem],
) -> AggregationProbabilityEntityStats:

    return AggregationProbabilityEntityStats(
        pulls_until_entity=initialize_empty_lists(items)
    )


def create_rarity_aggregation_stats(
    rarities: list[NormalizedRarity],
) -> AggregationRarityStats:

    return AggregationRarityStats(
        pulls_until_entity=initialize_empty_lists(rarities),
        pulls_until_completion=initialize_empty_lists(rarities),
    )


def create_simulation_aggregation_stats(
    rarities: list[NormalizedRarity],
) -> SimulationAggregationStats:
    item_stats = create_item_aggregation_stats(
        [item for rarity in rarities for item in rarity.items]
    )
    rarity_stats = create_rarity_aggregation_stats(rarities)
    return SimulationAggregationStats(item_stats=item_stats, rarity_stats=rarity_stats)


def update_simulation_aggregation_stats_per_pull(
    pull_result: PullResult,
    current_total_pulls: int,
    stats: SimulationAggregationStats,
):
    rarity_name = pull_result.rarity.name
    item_name = pull_result.item.name

    if pull_result.is_item_first_pull:
        stats.item_stats.pulls_until_entity[item_name].append(current_total_pulls)

    if pull_result.is_rarity_first_pull:
        stats.rarity_stats.pulls_until_entity[rarity_name].append(current_total_pulls)

    if pull_result.is_rarity_complete:
        stats.rarity_stats.pulls_until_completion[rarity_name].append(
            current_total_pulls
        )


def update_simulation_aggregation_stats_per_simulation(
    aggregation_stats: SimulationAggregationStats,
    total_duplicates: int,
    total_currency: float,
) -> None:
    aggregation_stats.total_currency_per_simulation.append(total_currency)
    aggregation_stats.duplicate_amounts_per_simulation.append(total_duplicates)
