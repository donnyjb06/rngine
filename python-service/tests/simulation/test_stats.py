from dataclasses import asdict
import pytest

from app.domain.models import NormalizedLootItem, NormalizedRarity
from app.simulation.types import (
    BatchItemStatsUpdate,
    BatchRarityStatsUpdate,
    BatchStatsUpdateData,
    SimulationTrackingStats,
)
from app.simulation.exceptions import SimulationEngineExecutionError
from app.simulation.util.aggregation import create_simulation_aggregation_stats
from app.simulation.util.stats import (
    create_descriptive_statistics,
    create_final_stats,
    create_simulation_batch_stats,
    create_simulation_stats,
    record_pull,
    update_simulation_batch_stats,
)
from tests.simulation.simulation_test_helpers import (
    build_tracking_pull_result,
    build_tracking_test_rarities,
)


def build_rarities():
    return [
        NormalizedRarity(
            name="Common",
            probability=50,
            items=[NormalizedLootItem(name="Knife", probability=100)],
        ),
        NormalizedRarity(
            name="Rare",
            probability=50,
            items=[
                NormalizedLootItem(name="Pistol", probability=50),
                NormalizedLootItem(name="Revolver", probability=50),
            ],
        ),
    ]


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


class TestCreateSimulationBatchStats:
    def setup_method(self):
        self.rarities = build_rarities()

    def test_initializes_total_counts_to_zero(self):
        global_stats = create_simulation_batch_stats(self.rarities).global_stats

        assert global_stats.total_duplicates == 0
        assert global_stats.total_currency == 0
        assert global_stats.total_pulls == 0

    def test_initializes_descriptive_stats_to_none(self):
        global_stats = asdict(create_simulation_batch_stats(self.rarities).global_stats)

        assert global_stats["mean_currency"] == None
        assert global_stats["median_currency"] == None
        assert global_stats["currency_stdev"] == None
        assert global_stats["average_duplicate_count"] == None


class TestUpdateSimulationBatchStatistics:
    def setup_method(self):
        self.rarities = build_rarities()

    def build_batch_update_stats(
        self,
        item_name: str = "Knife",
        rarity_name: str = "Common",
        total_pulls: int = 2,
    ):
        item_update_data: BatchItemStatsUpdate = {
            "pull_counts": {item_name: 2},
            "duplicate_amounts": {item_name: 1},
        }
        rarity_update_data: BatchRarityStatsUpdate = {
            "currency_amounts": {rarity_name: 2000},
            "pull_counts": {rarity_name: 2},
        }
        batch_update_data: BatchStatsUpdateData = {
            "item_data": item_update_data,
            "rarity_data": rarity_update_data,
            "global_data": {
                "total_pulls": total_pulls,
                "total_duplicates": 2,
                "total_currency": 4000,
            },
        }

        return batch_update_data

    def test_correctly_updates_entity_stats(self):
        batch_update_data = self.build_batch_update_stats()
        batch_stats = create_simulation_batch_stats(self.rarities)

        update_simulation_batch_stats(batch_update_data, batch_stats)

        assert batch_stats.item_stats.pull_counts["Knife"] == 2
        assert batch_stats.item_stats.duplicate_amounts["Knife"] == 1
        assert batch_stats.rarity_stats.pull_counts["Common"] == 2
        assert batch_stats.rarity_stats.currency_amounts["Common"] == 2000

    def test_raises_error_when_update_data_contains_unknown_item_name(self):
        batch_updates_data = self.build_batch_update_stats(item_name="knife")
        batch_stats = create_simulation_batch_stats(self.rarities)

        with pytest.raises(SimulationEngineExecutionError, match="item"):
            update_simulation_batch_stats(batch_updates_data, batch_stats)

    def test_raises_key_error_when_update_data_contains_unknown_rarity_name(self):
        batch_updates_data = self.build_batch_update_stats(rarity_name="commmon")
        batch_stats = create_simulation_batch_stats(self.rarities)

        with pytest.raises(SimulationEngineExecutionError, match="rarity"):
            update_simulation_batch_stats(batch_updates_data, batch_stats)

    def test_correctly_updates_global_stats(self):
        batch_updates_data = self.build_batch_update_stats()
        batch_stats = create_simulation_batch_stats(self.rarities)

        update_simulation_batch_stats(batch_updates_data, batch_stats)

        assert batch_stats.global_stats.total_currency == 4000
        assert batch_stats.global_stats.total_duplicates == 2
        assert batch_stats.global_stats.total_pulls == 2

    def test_raises_value_error_if_total_count_is_negative(self):
        batch_updates_data = self.build_batch_update_stats(total_pulls=-4)
        batch_stats = create_simulation_batch_stats(self.rarities)

        with pytest.raises(SimulationEngineExecutionError):
            update_simulation_batch_stats(batch_updates_data, batch_stats)


class TestCreateDescriptiveStatistics:
    def test_calculates_currency_and_duplicate_descriptive_statistics(self):
        aggregation_stats = create_simulation_aggregation_stats(build_rarities())
        aggregation_stats.total_currency_per_simulation.extend([100, 200, 300])
        aggregation_stats.duplicate_amounts_per_simulation.extend([1, 2, 3])

        global_stats = create_descriptive_statistics(aggregation_stats)

        assert global_stats.mean_currency == 200
        assert global_stats.median_currency == 200
        assert global_stats.currency_stdev == 100
        assert global_stats.average_duplicate_count == 2

    def test_leaves_optional_statistics_as_none_when_no_simulations_exist(self):
        aggregation_stats = create_simulation_aggregation_stats(build_rarities())

        global_stats = create_descriptive_statistics(aggregation_stats)

        assert global_stats.mean_currency is None
        assert global_stats.median_currency is None
        assert global_stats.currency_stdev is None
        assert global_stats.average_duplicate_count is None


class TestCreateFinalStats:
    def test_adds_descriptive_global_stats_and_returns_final_stats(self):
        rarities = build_rarities()
        aggregation_stats = create_simulation_aggregation_stats(rarities)
        batch_stats = create_simulation_batch_stats(rarities)
        aggregation_stats.total_currency_per_simulation.extend([100, 200, 300])
        aggregation_stats.duplicate_amounts_per_simulation.extend([1, 2, 3])
        aggregation_stats.item_stats.pulls_until_entity["Knife"].extend([1, 3])
        aggregation_stats.item_stats.pulls_until_entity["Pistol"].extend([4])
        aggregation_stats.rarity_stats.pulls_until_entity["Common"].extend([1, 5])
        aggregation_stats.rarity_stats.pulls_until_entity["Rare"].extend([2, 6])
        aggregation_stats.rarity_stats.pulls_until_completion["Common"].extend(
            [7, 9]
        )
        aggregation_stats.rarity_stats.pulls_until_completion["Rare"].extend([8])
        batch_stats.global_stats.total_pulls = 9
        batch_stats.global_stats.total_duplicates = 6
        batch_stats.global_stats.total_currency = 600
        batch_stats.item_stats.pull_counts = {
            "Knife": 4,
            "Pistol": 3,
            "Revolver": 2,
        }
        batch_stats.rarity_stats.pull_counts = {
            "Common": 4,
            "Rare": 5,
        }

        final_stats = create_final_stats(aggregation_stats, batch_stats, rarities)

        assert final_stats["batch"].global_stats.total_pulls == 9
        assert final_stats["batch"].global_stats.total_duplicates == 6
        assert final_stats["batch"].global_stats.total_currency == 600
        assert final_stats["batch"].global_stats.mean_currency == 200
        assert final_stats["batch"].global_stats.median_currency == 200
        assert final_stats["batch"].global_stats.currency_stdev == 100
        assert final_stats["batch"].global_stats.average_duplicate_count == 2
        assert final_stats["batch"].item_stats.expected_probability == {
            "Knife": 50,
            "Pistol": 25,
            "Revolver": 25,
        }
        assert final_stats["batch"].item_stats.observed_probability == {
            "Knife": pytest.approx(44.44444444444444),
            "Pistol": pytest.approx(33.33333333333333),
            "Revolver": pytest.approx(22.22222222222222),
        }
        assert final_stats["batch"].item_stats.average_pulls_until_entity == {
            "Knife": 2,
            "Pistol": 4,
        }
        assert final_stats["batch"].rarity_stats.expected_probability == {
            "Common": 50,
            "Rare": 50,
        }
        assert final_stats["batch"].rarity_stats.observed_probability == {
            "Common": pytest.approx(44.44444444444444),
            "Rare": pytest.approx(55.55555555555556),
        }
        assert final_stats["batch"].rarity_stats.average_pulls_until_entity == {
            "Common": 3,
            "Rare": 4,
        }
        assert final_stats["batch"].rarity_stats.average_pulls_until_completion == {
            "Common": 8,
            "Rare": 8,
        }
        assert final_stats["aggregation"] is aggregation_stats
