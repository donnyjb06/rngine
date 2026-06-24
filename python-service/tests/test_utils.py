import pytest

from app.domain.models import (
    RawLootItem,
    RawRarity,
    RawSimulationConfig,
    NormalizedLootItem,
    NormalizedRarity,
    NormalizedSimulationConfig,
)
from app.simulation.exceptions import (
    InvalidProbabilityError,
    InvalidWeightError,
    SimulationConfigError,
)

from app.utils import (
    getTotalWeight,
    require_weight,
    validate_weight,
    validate_config,
    validate_percentages,
    normalize_items_for_rarity,
    normalize_rarity,
    normalize_config,
)


class TestGetTotalWeight:
    def test_handles_empty_list(self):
        assert getTotalWeight([]) == 0

    def test_handles_all_weights_none(self):
        entities = [RawLootItem(name="Test Item 1"), RawLootItem(name="Test Item 2")]

        assert getTotalWeight(entities) == 0

    def test_handles_negative_weights(self):
        entities = [
            RawLootItem(name="Test Item 1", weight=-10),
            RawLootItem(name="Test Item 2", weight=-20),
        ]

        with pytest.raises(InvalidWeightError):
            getTotalWeight(entities)

    def test_handles_valid_values(self):
        entities = [
            RawLootItem(name="Test Item 1", weight=1),
            RawLootItem(name="Test Item 2", weight=3),
            RawLootItem(name="Test Item 2", weight=2),
        ]

        assert getTotalWeight(entities) == 6


class TestRequireWeight:
    def test_handles_rarity_weight(self):
        entity = RawRarity(name="Test Rarity", weight=2, items=[])

        assert require_weight(entity) == 2

    def test_handles_item_weight(self):
        entity = RawLootItem(name="Test Item", weight=5)

        assert require_weight(entity) == 5

    def test_handles_weight_none(self):
        entity = RawLootItem(name="Test Item")

        with pytest.raises(InvalidWeightError):
            require_weight(entity)

    def test_handles_weight_zero(self):
        entity = RawLootItem(name="Test Item", weight=0)

        with pytest.raises(InvalidWeightError):
            require_weight(entity)

class TestValidateWeight:
    def test_allows_valid_rarity_and_item_weights(self):
        rarities = [
            RawRarity(
                name="Common",
                weight=60,
                items=[
                    RawLootItem(name="Sword", weight=70),
                    RawLootItem(name="Shield", weight=30),
                ],
            )
        ]

        validate_weight(rarities, "item_probability")

    def test_raises_when_rarity_weight_is_missing(self):
        rarities = [
            RawRarity(
                name="Common",
                items=[RawLootItem(name="Sword", weight=10)],
            )
        ]

        with pytest.raises(
            InvalidWeightError, match="Common must have a non-negative weight"
        ):
            validate_weight(rarities, "item_probability")

    def test_raises_when_rarity_weight_is_negative(self):
        rarities = [
            RawRarity(
                name="Common",
                weight=-1,
                items=[RawLootItem(name="Sword", weight=10)],
            )
        ]

        with pytest.raises(
            InvalidWeightError, match="Common must have a non-negative weight"
        ):
            validate_weight(rarities, "item_probability")

    def test_raises_when_item_weight_is_missing_in_item_probability_mode(self):
        rarities = [
            RawRarity(
                name="Common",
                weight=60,
                items=[RawLootItem(name="Sword")],
            )
        ]

        with pytest.raises(
            InvalidWeightError,
            match="Sword in rarity Common must have a non-negative weight",
        ):
            validate_weight(rarities, "item_probability")

    def test_does_not_require_item_weights_in_equal_chance_mode(self):
        rarities = [
            RawRarity(
                name="Common",
                weight=60,
                items=[RawLootItem(name="Sword")],
            )
        ]

        validate_weight(rarities, "equal_chance")


class TestValidateConfig:
    def test_allows_valid_percentage_config(self):
        config = RawSimulationConfig(
            simulation_count=10,
            pulls_per_simulation=5,
            duplicate_mode="allow_duplicates",
            seed=None,
            item_selection_mode="item_probability",
            probability_mode="percentage",
            rarities=[
                RawRarity(
                    name="Common",
                    probability=100,
                    items=[RawLootItem(name="Sword", probability=100)],
                )
            ],
        )

        validate_config(config)

    def test_raises_when_simulation_count_is_zero(self):
        config = RawSimulationConfig(
            simulation_count=0,
            pulls_per_simulation=5,
            duplicate_mode="allow_duplicates",
            seed=None,
            item_selection_mode="item_probability",
            probability_mode="percentage",
            rarities=[
                RawRarity(
                    name="Common",
                    probability=100,
                    items=[RawLootItem(name="Sword", probability=100)],
                )
            ],
        )

        with pytest.raises(
            SimulationConfigError, match="simulation_count must be greater than 0"
        ):
            validate_config(config)

    def test_raises_when_pulls_per_simulation_is_zero(self):
        config = RawSimulationConfig(
            simulation_count=10,
            pulls_per_simulation=0,
            duplicate_mode="allow_duplicates",
            seed=None,
            item_selection_mode="item_probability",
            probability_mode="percentage",
            rarities=[
                RawRarity(
                    name="Common",
                    probability=100,
                    items=[RawLootItem(name="Sword", probability=100)],
                )
            ],
        )

        with pytest.raises(
            SimulationConfigError, match="pulls_per_simulation must be greater than 0"
        ):
            validate_config(config)

    def test_raises_when_hard_prevention_does_not_have_enough_items(self):
        config = RawSimulationConfig(
            simulation_count=1,
            pulls_per_simulation=3,
            duplicate_mode="hard_prevention",
            seed=None,
            item_selection_mode="item_probability",
            probability_mode="percentage",
            rarities=[
                RawRarity(
                    name="Common",
                    probability=100,
                    items=[
                        RawLootItem(name="Sword", probability=50),
                        RawLootItem(name="Shield", probability=50),
                    ],
                )
            ],
        )

        with pytest.raises(
            SimulationConfigError,
            match="Not enough items in rarity Common to prevent duplicates",
        ):
            validate_config(config)

    def test_weight_mode_calls_weight_validation(self):
        config = RawSimulationConfig(
            simulation_count=10,
            pulls_per_simulation=5,
            duplicate_mode="allow_duplicates",
            seed=None,
            item_selection_mode="item_probability",
            probability_mode="weight",
            rarities=[
                RawRarity(
                    name="Common",
                    items=[RawLootItem(name="Sword", weight=100)],
                )
            ],
        )

        with pytest.raises(
            InvalidWeightError, match="Common must have a non-negative weight"
        ):
            validate_config(config)


class TestValidatePercentages:
    def test_allows_valid_percentages(self):
        config = NormalizedSimulationConfig(
            simulation_count=10,
            pulls_per_simulation=5,
            duplicate_mode="allow_duplicates",
            seed=None,
            item_selection_mode="item_probability",
            rarities=[
                NormalizedRarity(
                    name="Common",
                    probability=60,
                    items=[NormalizedLootItem(name="Sword", probability=100)],
                ),
                NormalizedRarity(
                    name="Rare",
                    probability=40,
                    items=[NormalizedLootItem(name="Axe", probability=100)],
                ),
            ],
        )

        validate_percentages(config)

    def test_allows_tiny_floating_point_overflow_for_rarity_total(self):
        config = NormalizedSimulationConfig(
            simulation_count=10,
            pulls_per_simulation=5,
            duplicate_mode="allow_duplicates",
            seed=None,
            item_selection_mode="item_probability",
            rarities=[
                NormalizedRarity(
                    name="Common",
                    probability=33.333333333333336,
                    items=[NormalizedLootItem(name="Sword", probability=100)],
                ),
                NormalizedRarity(
                    name="Rare",
                    probability=33.333333333333336,
                    items=[NormalizedLootItem(name="Axe", probability=100)],
                ),
                NormalizedRarity(
                    name="Epic",
                    probability=33.333333333333336,
                    items=[NormalizedLootItem(name="Bow", probability=100)],
                ),
            ],
        )

        validate_percentages(config)

    def test_raises_when_total_rarity_probability_exceeds_100(self):
        config = NormalizedSimulationConfig(
            simulation_count=10,
            pulls_per_simulation=5,
            duplicate_mode="allow_duplicates",
            seed=None,
            item_selection_mode="item_probability",
            rarities=[
                NormalizedRarity(
                    name="Common",
                    probability=60,
                    items=[NormalizedLootItem(name="Sword", probability=100)],
                ),
                NormalizedRarity(
                    name="Rare",
                    probability=50,
                    items=[NormalizedLootItem(name="Axe", probability=100)],
                ),
            ],
        )

        with pytest.raises(
            InvalidProbabilityError,
            match="Total rarity probabilities must not exceed 100%",
        ):
            validate_percentages(config)

    def test_raises_when_total_item_probability_exceeds_100(self):
        config = NormalizedSimulationConfig(
            simulation_count=10,
            pulls_per_simulation=5,
            duplicate_mode="allow_duplicates",
            seed=None,
            item_selection_mode="item_probability",
            rarities=[
                NormalizedRarity(
                    name="Common",
                    probability=100,
                    items=[
                        NormalizedLootItem(name="Sword", probability=60),
                        NormalizedLootItem(name="Shield", probability=50),
                    ],
                )
            ],
        )

        with pytest.raises(
            InvalidProbabilityError,
            match="Total item probabilities in rarity Common must not exceed 100%",
        ):
            validate_percentages(config)


class TestNormalizeItemsForRarity:
    def test_normalizes_items_with_equal_chance(self):
        rarity = RawRarity(
            name="Common",
            probability=100,
            items=[
                RawLootItem(name="Sword"),
                RawLootItem(name="Shield"),
            ],
        )

        result = normalize_items_for_rarity(rarity, "equal_chance", "percentage")

        assert len(result) == 2
        assert result[0].probability == pytest.approx(50)
        assert result[1].probability == pytest.approx(50)

    def test_normalizes_items_using_weights(self):
        rarity = RawRarity(
            name="Common",
            weight=100,
            items=[
                RawLootItem(name="Sword", weight=25),
                RawLootItem(name="Shield", weight=75),
            ],
        )

        result = normalize_items_for_rarity(rarity, "item_probability", "weight")

        assert result[0].probability == pytest.approx(25)
        assert result[1].probability == pytest.approx(75)

    def test_uses_existing_item_percentages_in_percentage_mode(self):
        rarity = RawRarity(
            name="Common",
            probability=100,
            items=[
                RawLootItem(name="Sword", probability=30),
                RawLootItem(name="Shield", probability=70),
            ],
        )

        result = normalize_items_for_rarity(rarity, "item_probability", "percentage")

        assert result[0].probability == pytest.approx(30)
        assert result[1].probability == pytest.approx(70)

    def test_preserves_item_data_when_normalizing(self):
        rarity = RawRarity(
            name="Common",
            probability=100,
            items=[
                RawLootItem(name="Sword", probability=100, value=25),
            ],
        )

        result = normalize_items_for_rarity(rarity, "item_probability", "percentage")

        assert result[0].name == "Sword"
        assert result[0].value == 25
        assert result[0].probability == pytest.approx(100)

    def test_raises_when_rarity_has_no_items(self):
        rarity = RawRarity(
            name="Common",
            probability=100,
            items=[],
        )

        with pytest.raises(SimulationConfigError, match="must have at least one item"):
            normalize_items_for_rarity(rarity, "equal_chance", "percentage")

    def test_raises_when_weight_mode_has_no_valid_total_weight(self):
        rarity = RawRarity(
            name="Common",
            weight=100,
            items=[
                RawLootItem(name="Sword"),
            ],
        )

        with pytest.raises(
            InvalidWeightError,
            match="Total weight for items in rarity Common cannot be zero",
        ):
            normalize_items_for_rarity(rarity, "item_probability", "weight")

    def test_raises_when_item_probability_is_missing_in_percentage_mode(self):
        rarity = RawRarity(
            name="Common",
            probability=100,
            items=[
                RawLootItem(name="Sword"),
            ],
        )

        with pytest.raises(
            InvalidProbabilityError,
            match="Sword in rarity Common must have a probability",
        ):
            normalize_items_for_rarity(rarity, "item_probability", "percentage")


class TestNormalizeRarity:
    def test_normalizes_rarity_using_weight(self):
        rarity = RawRarity(
            name="Common",
            weight=25,
            items=[
                RawLootItem(name="Sword", weight=100),
            ],
        )

        result = normalize_rarity(
            rarity=rarity,
            total_rarity_weight=100,
            item_selection_mode="item_probability",
            probability_mode="weight",
        )

        assert result.name == "Common"
        assert result.probability == pytest.approx(25)
        assert result.items[0].probability == pytest.approx(100)

    def test_normalizes_rarity_using_percentage(self):
        rarity = RawRarity(
            name="Common",
            probability=60,
            items=[
                RawLootItem(name="Sword", probability=100),
            ],
        )

        result = normalize_rarity(
            rarity=rarity,
            total_rarity_weight=None,
            item_selection_mode="item_probability",
            probability_mode="percentage",
        )

        assert result.name == "Common"
        assert result.probability == pytest.approx(60)
        assert result.items[0].probability == pytest.approx(100)

    def test_raises_when_total_rarity_weight_is_missing_in_weight_mode(self):
        rarity = RawRarity(
            name="Common",
            weight=100,
            items=[
                RawLootItem(name="Sword", weight=100),
            ],
        )

        with pytest.raises(InvalidWeightError, match="Total rarity weight is required"):
            normalize_rarity(
                rarity=rarity,
                total_rarity_weight=None,
                item_selection_mode="item_probability",
                probability_mode="weight",
            )

    def test_raises_when_rarity_probability_is_missing_in_percentage_mode(self):
        rarity = RawRarity(
            name="Common",
            items=[
                RawLootItem(name="Sword", probability=100),
            ],
        )

        with pytest.raises(InvalidProbabilityError, match="probability must exist"):
            normalize_rarity(
                rarity=rarity,
                total_rarity_weight=None,
                item_selection_mode="item_probability",
                probability_mode="percentage",
            )


class TestNormalizeConfig:
    def test_normalizes_full_weight_based_config(self):
        config = RawSimulationConfig(
            simulation_count=10,
            pulls_per_simulation=5,
            duplicate_mode="allow_duplicates",
            seed=123,
            item_selection_mode="item_probability",
            probability_mode="weight",
            rarities=[
                RawRarity(
                    name="Common",
                    weight=75,
                    items=[
                        RawLootItem(name="Sword", weight=60),
                        RawLootItem(name="Shield", weight=40),
                    ],
                ),
                RawRarity(
                    name="Rare",
                    weight=25,
                    items=[
                        RawLootItem(name="Axe", weight=100),
                    ],
                ),
            ],
        )

        result = normalize_config(config)

        assert result.simulation_count == 10
        assert result.pulls_per_simulation == 5
        assert result.duplicate_mode == "allow_duplicates"
        assert result.seed == 123
        assert result.item_selection_mode == "item_probability"

        assert result.rarities[0].name == "Common"
        assert result.rarities[0].probability == pytest.approx(75)
        assert result.rarities[0].items[0].probability == pytest.approx(60)
        assert result.rarities[0].items[1].probability == pytest.approx(40)

        assert result.rarities[1].name == "Rare"
        assert result.rarities[1].probability == pytest.approx(25)
        assert result.rarities[1].items[0].probability == pytest.approx(100)

    def test_normalizes_full_percentage_based_config(self):
        config = RawSimulationConfig(
            simulation_count=10,
            pulls_per_simulation=5,
            duplicate_mode="duplicate_currency",
            seed=None,
            item_selection_mode="item_probability",
            probability_mode="percentage",
            rarities=[
                RawRarity(
                    name="Common",
                    probability=80,
                    items=[
                        RawLootItem(name="Sword", probability=50),
                        RawLootItem(name="Shield", probability=50),
                    ],
                ),
                RawRarity(
                    name="Rare",
                    probability=20,
                    items=[
                        RawLootItem(name="Axe", probability=100),
                    ],
                ),
            ],
        )

        result = normalize_config(config)

        assert result.duplicate_mode == "duplicate_currency"
        assert result.rarities[0].probability == pytest.approx(80)
        assert result.rarities[0].items[0].probability == pytest.approx(50)
        assert result.rarities[0].items[1].probability == pytest.approx(50)
        assert result.rarities[1].probability == pytest.approx(20)
        assert result.rarities[1].items[0].probability == pytest.approx(100)
