from statistics import mean, median, stdev
from typing import cast
from app.domain.models import (
    NormalizedLootItem,
    NormalizedRarity,
)
from app.simulation.types import (
    BatchGlobalStatsUpdate,
    BatchItemStats,
    BatchItemStatsUpdate,
    BatchRarityStats,
    BatchRarityStatsUpdate,
    BatchStatsUpdateData,
    DuplicationConfig,
    FinalStats,
    GlobalStats,
    ItemStats,
    PullResult,
    RarityStats,
    SimulationAggregationStats,
    SimulationBatchStats,
    SimulationStats,
    SimulationTrackingStats,
)
from app.simulation.util.aggregation import update_simulation_aggregation_stats_per_pull


def create_rarity_stats(rarities: list[NormalizedRarity]) -> RarityStats:
    initial_counts = {rarity.name: 0 for rarity in rarities}

    return RarityStats(
        pull_counts=initial_counts.copy(), currency_amounts=initial_counts.copy()
    )


def create_item_stats(items: list[NormalizedLootItem]) -> ItemStats:
    initial_counts = {item.name: 0 for item in items}

    return ItemStats(
        pull_counts=initial_counts.copy(),
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

    if pull_result.is_duplicate:
        stats.total_duplicates += 1

        if duplication_config["are_duplicate_possible"]:
            stats.item_stats.duplicate_amounts[item_name] += 1

    stats.rarity_stats.pull_counts[rarity_name] += 1
    stats.item_stats.pull_counts[item_name] += 1


def create_batch_update_data(
    simulation_stats: SimulationStats,
) -> BatchStatsUpdateData:
    total_pulls = sum(simulation_stats.rarity_stats.pull_counts.values())

    return {
        "item_data": {
            "pull_counts": simulation_stats.item_stats.pull_counts.copy(),
            "duplicate_amounts": simulation_stats.item_stats.duplicate_amounts.copy(),
        },
        "rarity_data": {
            "pull_counts": simulation_stats.rarity_stats.pull_counts.copy(),
            "currency_amounts": simulation_stats.rarity_stats.currency_amounts.copy(),
        },
        "global_data": {
            "total_pulls": total_pulls,
            "total_duplicates": simulation_stats.total_duplicates,
            "total_currency": simulation_stats.total_currency,
        },
    }


def update_batch_item_stats(
    item_data: BatchItemStatsUpdate, batch_stats: SimulationBatchStats
) -> None:
    for name, amount in item_data["duplicate_amounts"].items():
        if name not in batch_stats.item_stats.duplicate_amounts:
            raise KeyError("Missing item in duplicate amounts dictionary")

        batch_stats.item_stats.duplicate_amounts[name] += amount

    for name, amount in item_data["pull_counts"].items():
        if name not in batch_stats.item_stats.pull_counts:
            raise KeyError("Missing item in pull counts list")

        batch_stats.item_stats.pull_counts[name] += amount


def update_batch_rarity_stats(
    rarity_data: BatchRarityStatsUpdate, batch_stats: SimulationBatchStats
) -> None:

    for name, amount in rarity_data["currency_amounts"].items():
        if name not in batch_stats.rarity_stats.currency_amounts:
            raise KeyError("Missing rarity in duplicate amounts dictionary")

        batch_stats.rarity_stats.currency_amounts[name] += amount

    for name, amount in rarity_data["pull_counts"].items():
        if name not in batch_stats.rarity_stats.pull_counts:
            raise KeyError("Missing rarity in pull counts list")

        batch_stats.rarity_stats.pull_counts[name] += amount


def update_global_batch_stats(
    global_stats: BatchGlobalStatsUpdate, batch_stats: SimulationBatchStats
) -> None:
    for value in global_stats.values():
        amount = cast(int, value)

        if amount < 0:
            raise ValueError(f"Total amount of {amount} is invalid")

    batch_stats.global_stats.total_currency += global_stats["total_currency"]
    batch_stats.global_stats.total_pulls += global_stats["total_pulls"]
    batch_stats.global_stats.total_duplicates += global_stats["total_duplicates"]


def update_simulation_batch_stats(
    batch_update_data: BatchStatsUpdateData, batch_stats: SimulationBatchStats
) -> None:
    update_batch_item_stats(batch_update_data["item_data"], batch_stats)
    update_batch_rarity_stats(batch_update_data["rarity_data"], batch_stats)
    update_global_batch_stats(batch_update_data["global_data"], batch_stats)


def create_rarity_batch_stats(rarities: list[NormalizedRarity]) -> BatchRarityStats:
    initial_counts = {rarity.name: 0 for rarity in rarities}

    return BatchRarityStats(
        currency_amounts=initial_counts.copy(), pull_counts=initial_counts.copy()
    )


def create_item_batch_stats(items: list[NormalizedLootItem]) -> BatchItemStats:
    initial_counts = {item.name: 0 for item in items}

    return BatchItemStats(
        duplicate_amounts=initial_counts.copy(), pull_counts=initial_counts.copy()
    )


def create_simulation_batch_stats(
    rarities: list[NormalizedRarity],
) -> SimulationBatchStats:
    items = [item for rarity in rarities for item in rarity.items]

    return SimulationBatchStats(
        global_stats=GlobalStats(),
        item_stats=create_item_batch_stats(items),
        rarity_stats=create_rarity_batch_stats(rarities),
    )


def calculate_expected_item_probability(
    rarities: list[NormalizedRarity],
) -> dict[str, float]:
    return {
        item.name: (item.probability * rarity.probability) / 100
        for rarity in rarities
        for item in rarity.items
    }


def calculate_expected_rarity_probability(
    rarities: list[NormalizedRarity],
) -> dict[str, float]:
    return {rarity.name: rarity.probability for rarity in rarities}


def calculate_observed_probability(
    pull_counts: dict[str, int],
    total_pulls: int,
) -> dict[str, float]:
    if total_pulls == 0:
        return {name: 0 for name in pull_counts}

    return {name: (count / total_pulls) * 100 for name, count in pull_counts.items()}


def calculate_average_pulls_until_entity(
    pulls_until_entity: dict[str, list[int]],
) -> dict[str, float]:
    return {
        name: mean(pull_counts)
        for name, pull_counts in pulls_until_entity.items()
        if pull_counts
    }


def calculate_average_pulls_until_completion(
    pulls_until_completion: dict[str, list[int]],
) -> dict[str, float]:
    return {
        name: mean(pull_counts)
        for name, pull_counts in pulls_until_completion.items()
        if pull_counts
    }


def create_final_item_batch_stats(
    item_stats: BatchItemStats,
    aggregation_stats: SimulationAggregationStats,
    rarities: list[NormalizedRarity],
    total_pulls: int,
) -> BatchItemStats:
    item_stats.expected_probability = calculate_expected_item_probability(rarities)
    item_stats.observed_probability = calculate_observed_probability(
        item_stats.pull_counts,
        total_pulls,
    )
    item_stats.average_pulls_until_entity = calculate_average_pulls_until_entity(
        aggregation_stats.item_stats.pulls_until_entity
    )

    return item_stats


def create_final_rarity_batch_stats(
    rarity_stats: BatchRarityStats,
    aggregation_stats: SimulationAggregationStats,
    rarities: list[NormalizedRarity],
    total_pulls: int,
) -> BatchRarityStats:
    rarity_stats.expected_probability = calculate_expected_rarity_probability(rarities)
    rarity_stats.observed_probability = calculate_observed_probability(
        rarity_stats.pull_counts,
        total_pulls,
    )
    rarity_stats.average_pulls_until_entity = calculate_average_pulls_until_entity(
        aggregation_stats.rarity_stats.pulls_until_entity
    )
    rarity_stats.average_pulls_until_completion = (
        calculate_average_pulls_until_completion(
            aggregation_stats.rarity_stats.pulls_until_completion
        )
    )

    return rarity_stats


def apply_final_entity_stats(
    batch_stats: SimulationBatchStats,
    rarities: list[NormalizedRarity],
    total_pulls: int,
    aggregation_stats: SimulationAggregationStats,
) -> None:

    batch_stats.item_stats = create_final_item_batch_stats(
        batch_stats.item_stats, aggregation_stats, rarities, total_pulls
    )
    batch_stats.rarity_stats = create_final_rarity_batch_stats(
        batch_stats.rarity_stats, aggregation_stats, rarities, total_pulls
    )


def create_descriptive_statistics(
    aggregation_stats: SimulationAggregationStats,
) -> GlobalStats:
    currency_per_simulation = aggregation_stats.total_currency_per_simulation
    duplicates_per_simulation = aggregation_stats.duplicate_amounts_per_simulation

    global_stats = GlobalStats()

    if currency_per_simulation:
        global_stats.mean_currency = mean(currency_per_simulation)
        global_stats.median_currency = median(currency_per_simulation)

    if len(currency_per_simulation) > 1:
        global_stats.currency_stdev = stdev(currency_per_simulation)

    if duplicates_per_simulation:
        global_stats.average_duplicate_count = mean(duplicates_per_simulation)

    return global_stats


def apply_final_descriptive_stats(
    batch_stats: SimulationBatchStats, descriptive_stats: GlobalStats
):
    batch_stats.global_stats.mean_currency = descriptive_stats.mean_currency
    batch_stats.global_stats.median_currency = descriptive_stats.median_currency
    batch_stats.global_stats.currency_stdev = descriptive_stats.currency_stdev
    batch_stats.global_stats.average_duplicate_count = (
        descriptive_stats.average_duplicate_count
    )


def create_final_stats(
    aggregation_stats: SimulationAggregationStats,
    batch_stats: SimulationBatchStats,
    rarities: list[NormalizedRarity],
) -> FinalStats:

    descriptive_stats = create_descriptive_statistics(aggregation_stats)
    apply_final_descriptive_stats(batch_stats, descriptive_stats)

    apply_final_entity_stats(
        batch_stats,
        rarities,
        aggregation_stats=aggregation_stats,
        total_pulls=batch_stats.global_stats.total_pulls,
    )

    return {
        "batch": batch_stats,
        "aggregation": aggregation_stats,
    }
