from app.domain.models import NormalizedRarity
from app.simulation.types import SimulationTrackingStats
from app.simulation.util.aggregation import create_simulation_aggregation_stats
from app.simulation.util.stats import create_simulation_stats, record_pull
from tests.simulation.simulation_test_helpers import (
    build_tracking_pull_result,
    build_tracking_test_rarities,
)


def build_tracking_stats(rarities: list[NormalizedRarity]) -> SimulationTrackingStats:
    return {
        "simulation": create_simulation_stats(rarities),
        "aggregation": create_simulation_aggregation_stats(rarities),
    }


class TestCreateSimulationStats:
    def test_initializes_rarity_and_item_stats_with_zero_counts(self):
        rarities = build_tracking_test_rarities()

        result = create_simulation_stats(rarities)

        assert result.total_currency == 0
        assert result.total_duplicates == 0
        assert result.rarity_stats.pull_counts == {"Common": 0, "Rare": 0}
        assert result.rarity_stats.currency_amounts == {"Common": 0, "Rare": 0}
        assert result.item_stats.pull_counts == {
            "AK-47": 0,
            "Glock": 0,
            "Knife": 0,
        }
        assert result.item_stats.currency_amounts == {
            "AK-47": 0,
            "Glock": 0,
            "Knife": 0,
        }
        assert result.item_stats.duplicate_amounts == {
            "AK-47": 0,
            "Glock": 0,
            "Knife": 0,
        }


class TestRecordPull:
    def test_updates_simulation_and_aggregation_stats_for_pull(self):
        rarities = build_tracking_test_rarities()
        stats = build_tracking_stats(rarities)
        pull_result = build_tracking_pull_result(
            rarities,
            currency_awarded=100,
            is_item_first_pull=True,
        )

        record_pull(
            stats,
            pull_result,
            {"is_hard_prevention": False, "are_duplicate_possible": True},
            current_total_pulls=3,
        )

        assert stats["simulation"].total_currency == 100
        assert stats["simulation"].total_duplicates == 0
        assert stats["simulation"].rarity_stats.pull_counts["Common"] == 1
        assert stats["simulation"].rarity_stats.currency_amounts["Common"] == 100
        assert stats["simulation"].item_stats.pull_counts["AK-47"] == 1
        assert stats["simulation"].item_stats.currency_amounts["AK-47"] == 100
        assert stats["aggregation"].item_stats.pulls_until_entity["AK-47"] == [3]

    def test_counts_duplicate_when_duplicates_are_possible(self):
        rarities = build_tracking_test_rarities()
        stats = build_tracking_stats(rarities)
        pull_result = build_tracking_pull_result(
            rarities,
            is_duplicate=True,
            currency_awarded=100,
        )

        record_pull(
            stats,
            pull_result,
            {"is_hard_prevention": False, "are_duplicate_possible": True},
            current_total_pulls=4,
        )

        assert stats["simulation"].total_duplicates == 1
        assert stats["simulation"].item_stats.duplicate_amounts["AK-47"] == 1

    def test_does_not_count_item_duplicate_when_duplicates_are_not_possible(self):
        rarities = build_tracking_test_rarities()
        stats = build_tracking_stats(rarities)
        pull_result = build_tracking_pull_result(
            rarities,
            is_duplicate=True,
            currency_awarded=100,
        )

        record_pull(
            stats,
            pull_result,
            {"is_hard_prevention": True, "are_duplicate_possible": False},
            current_total_pulls=4,
        )

        assert stats["simulation"].total_duplicates == 1
        assert stats["simulation"].item_stats.duplicate_amounts["AK-47"] == 0
