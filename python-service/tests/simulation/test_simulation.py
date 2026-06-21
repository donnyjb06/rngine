from typing import Literal
from random import Random
from app.domain.models import (
    NormalizedLootItem,
    NormalizedRarity,
    NormalizedSimulationConfig,
)
from app.simulation.simulation import run_simulation, run_simulation_batch
from app.simulation.types import CurrencyMap, SimulationTrackingStats
from app.simulation.util.aggregation import create_simulation_aggregation_stats
from app.simulation.util.stats import create_simulation_stats


def build_run_simulation_rarities() -> list[NormalizedRarity]:
    return [
        NormalizedRarity(
            name="Common",
            probability=80,
            items=[
                NormalizedLootItem(name="AK-47", probability=70),
                NormalizedLootItem(name="Glock", probability=30),
            ],
        ),
        NormalizedRarity(
            name="Rare",
            probability=20,
            items=[
                NormalizedLootItem(name="Knife", probability=100),
            ],
        ),
    ]


def build_run_simulation_config(
    *,
    simulation_count: int = 1,
    pulls_per_simulation: int = 10,
    duplicate_mode: Literal[
        "allow_duplicates", "hard_prevention", "duplicate_currency"
    ] = "allow_duplicates",
    seed: int | None = 1234,
    item_selection_mode: Literal[
        "item_probability", "equal_chance"
    ] = "item_probability",
    rarities: list[NormalizedRarity] | None = None,
) -> NormalizedSimulationConfig:
    return NormalizedSimulationConfig(
        simulation_count=simulation_count,
        pulls_per_simulation=pulls_per_simulation,
        duplicate_mode=duplicate_mode,
        seed=seed,
        item_selection_mode=item_selection_mode,
        rarities=rarities or build_run_simulation_rarities(),
    )


def build_run_simulation_tracking_stats(
    rarities: list[NormalizedRarity] | None = None,
) -> SimulationTrackingStats:
    test_rarities = rarities or build_run_simulation_rarities()

    return {
        "simulation": create_simulation_stats(test_rarities),
        "aggregation": create_simulation_aggregation_stats(test_rarities),
    }


def build_run_simulation_currency_map(
    rarities: list[NormalizedRarity] | None = None,
) -> CurrencyMap:
    test_rarities = rarities or build_run_simulation_rarities()

    return {rarity.name: index * 100 for index, rarity in enumerate(test_rarities, 1)}


class TestRunSimulation:
    def test_records_expected_number_of_pulls_when_duplicates_are_allowed(self):
        config = build_run_simulation_config(
            duplicate_mode="allow_duplicates",
            pulls_per_simulation=5,
        )
        tracking_stats = build_run_simulation_tracking_stats(config.rarities)
        currency_map = build_run_simulation_currency_map(config.rarities)
        rng = Random(config.seed)

        run_simulation(config, tracking_stats, currency_map, rng)

        assert sum(tracking_stats["simulation"].rarity_stats.pull_counts.values()) == 5
        assert sum(tracking_stats["simulation"].item_stats.pull_counts.values()) == 5

    def test_records_duplicate_currency_when_duplicate_currency_mode_repulls_item(self):
        rarities = [
            NormalizedRarity(
                name="Common",
                probability=100,
                items=[
                    NormalizedLootItem(name="AK-47", probability=100),
                ],
            ),
        ]
        config = build_run_simulation_config(
            duplicate_mode="duplicate_currency",
            pulls_per_simulation=3,
            rarities=rarities,
        )
        tracking_stats = build_run_simulation_tracking_stats(config.rarities)
        currency_map = {"Common": 100}
        rng = Random(config.seed)

        run_simulation(config, tracking_stats, currency_map, rng)

        assert tracking_stats["simulation"].item_stats.pull_counts["AK-47"] == 3
        assert tracking_stats["simulation"].total_duplicates == 2
        assert tracking_stats["simulation"].item_stats.duplicate_amounts["AK-47"] == 2
        assert tracking_stats["simulation"].total_currency == 200

    def test_stops_hard_prevention_simulation_when_all_items_are_exhausted(self):
        config = build_run_simulation_config(
            duplicate_mode="hard_prevention",
            pulls_per_simulation=10,
        )
        tracking_stats = build_run_simulation_tracking_stats(config.rarities)
        currency_map = build_run_simulation_currency_map(config.rarities)
        rng = Random(config.seed)

        run_simulation(config, tracking_stats, currency_map, rng)

        assert sum(tracking_stats["simulation"].rarity_stats.pull_counts.values()) == 3
        assert sum(tracking_stats["simulation"].item_stats.pull_counts.values()) == 3
        assert tracking_stats["simulation"].total_duplicates == 0

    def test_records_rarity_completion_in_hard_prevention_mode(self):
        rarities = [
            NormalizedRarity(
                name="Common",
                probability=100,
                items=[
                    NormalizedLootItem(name="AK-47", probability=100),
                ],
            ),
        ]
        config = build_run_simulation_config(
            duplicate_mode="hard_prevention",
            pulls_per_simulation=10,
            rarities=rarities,
        )
        tracking_stats = build_run_simulation_tracking_stats(config.rarities)
        currency_map = {"Common": 100}
        rng = Random(config.seed)

        run_simulation(config, tracking_stats, currency_map, rng)

        assert tracking_stats["simulation"].item_stats.pull_counts["AK-47"] == 1
        assert tracking_stats["aggregation"].item_stats.pulls_until_entity["AK-47"] == [
            1
        ]
        assert tracking_stats["aggregation"].rarity_stats.pulls_until_completion[
            "Common"
        ] == [1]


class TestRunSimulationBatch:
    def test_returns_correct_final_aggregated_stats(self):
        config = build_run_simulation_config()

        final_stats = run_simulation_batch(config)

        assert final_stats["batch"].global_stats.total_duplicates == 9
        assert (
            final_stats["batch"].global_stats.total_pulls
            == config.pulls_per_simulation * config.simulation_count
        )
