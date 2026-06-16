from app.simulation.types import (
    AggregationProbabilityEntityStats,
    AggregationRarityStats,
    SimulationAggregationStats,
)
from app.simulation.util.aggregation import (
    create_simulation_aggregation_stats,
    update_simulation_aggregation_stats_per_pull,
    update_simulation_aggregation_stats_per_simulation,
)
from tests.simulation.simulation_test_helpers import (
    build_tracking_pull_result,
    build_tracking_test_rarities,
)


class TestCreateSimulationAggregationStats:
    def test_initializes_item_and_rarity_aggregation_lists(self):
        rarities = build_tracking_test_rarities()

        result = create_simulation_aggregation_stats(rarities)

        assert result.item_stats.pulls_until_entity == {
            "AK-47": [],
            "Glock": [],
            "Knife": [],
        }
        assert result.rarity_stats.pulls_until_entity == {
            "Common": [],
            "Rare": [],
        }
        assert result.rarity_stats.pulls_until_completion == {
            "Common": [],
            "Rare": [],
        }
        assert result.total_currency_per_simulation == []
        assert result.duplicate_amounts_per_simulation == []


class TestUpdateSimulationAggregationStatsPerPull:
    def test_records_first_item_pull_count(self):
        rarities = build_tracking_test_rarities()
        stats = create_simulation_aggregation_stats(rarities)
        pull_result = build_tracking_pull_result(
            rarities,
            is_item_first_pull=True,
        )

        update_simulation_aggregation_stats_per_pull(
            pull_result,
            current_total_pulls=2,
            stats=stats,
        )

        assert stats.item_stats.pulls_until_entity["AK-47"] == [2]

    def test_records_first_rarity_pull_count(self):
        rarities = build_tracking_test_rarities()
        stats = create_simulation_aggregation_stats(rarities)
        pull_result = build_tracking_pull_result(
            rarities,
            is_rarity_first_pull=True,
        )

        update_simulation_aggregation_stats_per_pull(
            pull_result,
            current_total_pulls=5,
            stats=stats,
        )

        assert stats.rarity_stats.pulls_until_entity["Common"] == [5]

    def test_records_rarity_completion_pull_count(self):
        rarities = build_tracking_test_rarities()
        stats = create_simulation_aggregation_stats(rarities)
        pull_result = build_tracking_pull_result(
            rarities,
            is_rarity_complete=True,
        )

        update_simulation_aggregation_stats_per_pull(
            pull_result,
            current_total_pulls=7,
            stats=stats,
        )

        assert stats.rarity_stats.pulls_until_completion["Common"] == [7]


class TestUpdateSimulationAggregationStatsPerSimulation:
    def build_aggregation_stats(self) -> SimulationAggregationStats:

        return SimulationAggregationStats(
            item_stats=AggregationProbabilityEntityStats(
                pulls_until_entity={"knife": [1, 2, 3]}
            ),
            rarity_stats=AggregationRarityStats(
                pulls_until_completion={"Common": [1, 2, 3]},
                pulls_until_entity={"Common": [1, 2, 3]},
            ),
        )

    def test_appends_total_simulation_amounts_to_aggregation_stats(self):
        total_currency = 5000
        total_duplicates = 5

        aggregation_stats = self.build_aggregation_stats()

        update_simulation_aggregation_stats_per_simulation(
            aggregation_stats, total_duplicates, total_currency
        )
        assert aggregation_stats.total_currency_per_simulation[0] == 5000
        assert aggregation_stats.duplicate_amounts_per_simulation[0] == 5
        assert len(aggregation_stats.total_currency_per_simulation) == 1
        assert len(aggregation_stats.duplicate_amounts_per_simulation) == 1
