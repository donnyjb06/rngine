from random import Random
from app import simulation
from app.domain import NormalizedSimulationConfig
from app.simulation import (
    build_simulation_state,
    create_pull_result,
    pull_item,
    update_state,
    record_pull,
)
from app.simulation.util import aggregation
from app.simulation.util.aggregation import (
    create_simulation_aggregation_stats,
    update_simulation_aggregation_stats_per_simulation,
)
from app.simulation.util.currency import build_rarity_currency_map
from app.simulation.util.random import generate_rng
from app.simulation.util.stats import (
    create_batch_update_data,
    create_final_stats,
    create_simulation_batch_stats,
    create_simulation_stats,
    update_simulation_batch_stats,
)
from .types import (
    CurrencyMap,
    DuplicationConfig,
    FinalStats,
    PullResult,
    PulledEntities,
    SimulationAggregationStats,
    SimulationStats,
    SimulationTrackingStats,
)


def run_simulation(
    config: NormalizedSimulationConfig,
    tracking_stats: SimulationTrackingStats,
    currency_map: CurrencyMap,
    rng: Random,
):
    state = build_simulation_state(config)

    for _ in range(config.pulls_per_simulation):
        pulled_entities: PulledEntities = pull_item(rng, state.endpoints)
        update_state(config, state, pulled_entities)
        pull_result: PullResult = create_pull_result(
            pulled_entities, state, currency_map
        )
        duplication_config: DuplicationConfig = DuplicationConfig(
            is_hard_prevention=config.duplicate_mode == "hard_prevention",
            are_duplicate_possible=config.duplicate_mode != "hard_prevention",
        )

        record_pull(
            tracking_stats, pull_result, duplication_config, state.current_total_pulls
        )

        if not state.eligible_items_by_rarity:
            break


def run_simulation_batch(config: NormalizedSimulationConfig) -> FinalStats:

    simulation_aggregation_stats: SimulationAggregationStats = (
        create_simulation_aggregation_stats(config.rarities)
    )
    rng = generate_rng(config.seed)
    currency_map = build_rarity_currency_map(config.rarities)
    simulation_batch_stats = create_simulation_batch_stats(config.rarities)

    for _ in range(config.simulation_count):
        simulation_stats: SimulationStats = create_simulation_stats(config.rarities)

        tracking_stats: SimulationTrackingStats = {
            "simulation": simulation_stats,
            "aggregation": simulation_aggregation_stats,
        }

        run_simulation(config, tracking_stats, currency_map, rng)
        update_simulation_aggregation_stats_per_simulation(
            tracking_stats["aggregation"],
            total_currency=tracking_stats["simulation"].total_currency,
            total_duplicates=tracking_stats["simulation"].total_duplicates,
        )

        batch_stats_update_data = create_batch_update_data(simulation_stats)
        update_simulation_batch_stats(batch_stats_update_data, simulation_batch_stats)

    final_stats = create_final_stats(
        simulation_aggregation_stats, simulation_batch_stats, config.rarities
    )

    return final_stats
