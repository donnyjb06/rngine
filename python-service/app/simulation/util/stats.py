from app.domain.models import NormalizedLootItem, NormalizedRarity
from app.simulation.types import (
    DuplicationConfig,
    ItemStats,
    ProbabilityEntityStats,
    PullResult,
    SimulationStats,
    SimulationTrackingStats,
)
from app.simulation.util.aggregation import update_simulation_aggregation_stats_per_pull


def create_rarity_stats(rarities: list[NormalizedRarity]) -> ProbabilityEntityStats:
    initial_counts = {rarity.name: 0 for rarity in rarities}

    return ProbabilityEntityStats(
        pull_counts=initial_counts.copy(), currency_amounts=initial_counts.copy()
    )


def create_item_stats(items: list[NormalizedLootItem]) -> ItemStats:
    initial_counts = {item.name: 0 for item in items}

    return ItemStats(
        pull_counts=initial_counts.copy(),
        currency_amounts=initial_counts.copy(),
        duplicate_amounts=initial_counts.copy(),
    )


def create_simulation_stats(rarities: list[NormalizedRarity]) -> SimulationStats:
    rarity_stats = create_rarity_stats(rarities)
    item_stats = create_item_stats(
        [item for rarity in rarities for item in rarity.items]
    )

    return SimulationStats(rarity_stats=rarity_stats, item_stats=item_stats)


def record_pull(
    stats: SimulationTrackingStats,
    pull_result,
    duplication_config: DuplicationConfig,
    current_total_pulls: int,
):
    update_simulation_stats(pull_result, duplication_config, stats["simulation"])
    update_simulation_aggregation_stats_per_pull(
        pull_result, current_total_pulls, stats["aggregation"]
    )


def update_simulation_stats(
    pull_result: PullResult,
    duplication_config: DuplicationConfig,
    stats: SimulationStats,
):
    rarity_name = pull_result.rarity.name
    item_name = pull_result.item.name

    stats.total_currency += pull_result.currency_awarded
    stats.rarity_stats.currency_amounts[rarity_name] += pull_result.currency_awarded
    stats.item_stats.currency_amounts[item_name] += pull_result.currency_awarded

    if pull_result.is_duplicate:
        stats.total_duplicates += 1

        if duplication_config["are_duplicate_possible"]:
            stats.item_stats.duplicate_amounts[item_name] += 1

    stats.rarity_stats.pull_counts[rarity_name] += 1
    stats.item_stats.pull_counts[item_name] += 1
