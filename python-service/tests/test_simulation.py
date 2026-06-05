import pytest
from random import Random

from app.domain.models import (
    NormalizedLootItem,
    NormalizedProbabilityEntity,
    NormalizedRarity,
    NormalizedSimulationConfig,
)
from app.simulation import (
    build_simulation_state,
    create_pull_result,
    generate_rng,
    update_state,
    get_next_random_value,
    generate_endpoint_data,
    get_next_entity,
    normalize_percentages,
    build_new_endpoint_data,
    build_rarity_currency_map,
    pull_item,
    CurrencyMap,
    EndpointData,
    Endpoints,
    SimulationState,
    PulledEntities,
)


def build_test_endpoints(rarities: list[NormalizedRarity]) -> Endpoints:
    return {
        "rarities": generate_endpoint_data((rarities)),
        "items": {
            rarity.name: generate_endpoint_data(rarity.items) for rarity in rarities
        },
    }


class TestGenerateRng:
    def test_returns_random_instance(self):
        rng = generate_rng(123)

        assert isinstance(rng, Random)

    def test_same_seed_produces_same_sequence(self):
        rng_one = generate_rng(123)
        rng_two = generate_rng(123)

        assert rng_one.random() == rng_two.random()
        assert rng_one.random() == rng_two.random()

    def test_different_seeds_produce_different_sequence(self):
        rng_one = generate_rng(123)
        rng_two = generate_rng(456)

        assert rng_one.random() != rng_two.random()


class TestGetNextRandomValue:
    def test_returns_value_between_0_and_100(self):
        rng = generate_rng(123)

        value = get_next_random_value(rng)

        assert 0 <= value <= 100

    def test_same_seed_produces_same_next_random_value(self):
        rng_one = generate_rng(123)
        rng_two = generate_rng(123)

        assert get_next_random_value(rng_one) == get_next_random_value(rng_two)


class TestGenerateEndpoints:
    def test_generates_cumulative_percentages_and_preserves_entities(self):
        entities = [
            NormalizedProbabilityEntity(name="Common", probability=50),
            NormalizedProbabilityEntity(name="Rare", probability=30),
            NormalizedProbabilityEntity(name="Epic", probability=20),
        ]

        result = generate_endpoint_data(entities)

        assert result["entities"] == entities
        assert result["percentages"] == pytest.approx([50, 80, 100])

    def test_returns_empty_endpoint_data_for_empty_entities(self):
        result = generate_endpoint_data([])

        assert result["entities"] == []
        assert result["percentages"] == []


class TestGetNextEntity:
    def test_returns_first_entity_when_random_number_is_inside_first_range(self):
        common = NormalizedProbabilityEntity(name="Common", probability=50)
        rare = NormalizedProbabilityEntity(name="Rare", probability=50)

        endpoints: EndpointData = {
            "entities": [common, rare],
            "percentages": [50, 100],
        }

        result = get_next_entity(endpoints, 25)

        assert result == common

    def test_returns_second_entity_when_random_number_is_inside_second_range(self):
        common = NormalizedProbabilityEntity(name="Common", probability=50)
        rare = NormalizedProbabilityEntity(name="Rare", probability=50)

        endpoints: EndpointData = {
            "entities": [common, rare],
            "percentages": [50, 100],
        }

        result = get_next_entity(endpoints, 75)

        assert result == rare

    def test_returns_entity_on_exact_endpoint_boundary(self):
        common = NormalizedProbabilityEntity(name="Common", probability=50)
        rare = NormalizedProbabilityEntity(name="Rare", probability=50)

        endpoints: EndpointData = {
            "entities": [common, rare],
            "percentages": [50, 100],
        }

        result = get_next_entity(endpoints, 50)

        assert result == common

    def test_raises_when_endpoint_lengths_do_not_match(self):
        common = NormalizedProbabilityEntity(name="Common", probability=50)

        endpoints: EndpointData = {
            "entities": [common],
            "percentages": [50, 100],
        }

        with pytest.raises(
            ValueError, match="entities and percentages length mismatch"
        ):
            get_next_entity(endpoints, 25)


class TestNormalizePercentages:
    def test_normalizes_probabilities_to_total_100(self):
        entities = [
            NormalizedProbabilityEntity(name="Common", probability=50),
            NormalizedProbabilityEntity(name="Epic", probability=20),
        ]

        result = normalize_percentages(entities)

        assert result[0].name == "Common"
        assert result[0].probability == pytest.approx(71.4285714286)

        assert result[1].name == "Epic"
        assert result[1].probability == pytest.approx(28.5714285714)

        assert sum(entity.probability for entity in result) == pytest.approx(100)

    def test_preserves_entity_names_when_normalizing(self):
        entities = [
            NormalizedProbabilityEntity(name="Rare", probability=30),
            NormalizedProbabilityEntity(name="Legendary", probability=10),
        ]

        result = normalize_percentages(entities)

        assert [entity.name for entity in result] == ["Rare", "Legendary"]

    def test_returns_empty_list_when_entities_is_empty(self):

        result = normalize_percentages([])
        assert result == []

    def test_raises_when_total_probability_is_zero(self):
        entities = [
            NormalizedProbabilityEntity(name="Broken One", probability=0),
            NormalizedProbabilityEntity(name="Broken Two", probability=0),
        ]

        with pytest.raises(
            ValueError, match="Total percentage must be greater than zero"
        ):
            normalize_percentages(entities)


class TestBuildNewEndpoints:
    def test_removes_entity_normalizes_remaining_entities_and_rebuilds_endpoints(self):
        common = NormalizedProbabilityEntity(name="Common", probability=50)
        rare = NormalizedProbabilityEntity(name="Rare", probability=30)
        epic = NormalizedProbabilityEntity(name="Epic", probability=20)

        result = build_new_endpoint_data(
            removed_entity=rare,
            entities=[common, rare, epic],
        )
        print(result)

        assert [entity.name for entity in result["entities"]] == ["Common", "Epic"]
        assert result["entities"][0].probability == pytest.approx(71.4285714286)
        assert result["entities"][1].probability == pytest.approx(28.5714285714)
        assert result["percentages"] == pytest.approx([71.4285714286, 100])

    def test_returns_empty_endpoints_when_removing_last_entity(self):
        common = NormalizedProbabilityEntity(name="Common", probability=100)

        result = build_new_endpoint_data(
            removed_entity=common,
            entities=[common],
        )

        expected_result: EndpointData = {"entities": [], "percentages": []}

        assert result == expected_result


class TestPullItem:
    def setup_method(self):
        self.rng = generate_rng(1234)

        self.guaranteed_item = NormalizedLootItem(name="Revolver", probability=100)
        self.revolver = NormalizedLootItem(name="Revolver", probability=50)
        self.dagger = NormalizedLootItem(name="Dagger", probability=50)
        self.ak47 = NormalizedLootItem(name="ak47", probability=30)
        self.ar15 = NormalizedLootItem(name="ar15", probability=30)
        self.glock = NormalizedLootItem(name="glock", probability=40)

        self.guaranteed_rarity = NormalizedRarity(
            name="Rare", probability=100, items=[self.guaranteed_item]
        )
        self.common_rarity = NormalizedRarity(
            name="common", probability=50, items=[self.ak47, self.ar15, self.glock]
        )
        self.rare_rarity = NormalizedRarity(
            name="rare", probability=50, items=[self.revolver, self.dagger]
        )
        self.endpoints_equal_rarity = build_test_endpoints(
            [self.rare_rarity, self.common_rarity]
        )

    def test_returns_item_and_rarity_if_100_probability(self):
        endpoints = build_test_endpoints([self.guaranteed_rarity])
        pull = pull_item(self.rng, endpoints)
        item, rarity = pull.item, pull.rarity

        assert item == self.guaranteed_item
        assert rarity == self.guaranteed_rarity

    def test_selects_correct_item_inside_rarity_items(self):
        pull = pull_item(self.rng, self.endpoints_equal_rarity)
        item, rarity = pull.item, pull.rarity

        assert item in rarity.items

    def test_same_seed_returns_same_result(self):
        rng1 = generate_rng(1234)
        rng2 = generate_rng(1234)

        pull_one = pull_item(rng1, self.endpoints_equal_rarity)
        pull_two = pull_item(rng2, self.endpoints_equal_rarity)

        assert pull_one == pull_two


class TestBuildSimulationState:
    def setup_method(self):
        self.config = NormalizedSimulationConfig(
            simulation_count=10,
            seed=1234,
            duplicate_mode="hard_prevention",
            item_selection_mode="item_probability",
            pulls_per_simulation=20,
            rarities=[
                NormalizedRarity(
                    name="Common",
                    probability=50,
                    items=[
                        NormalizedLootItem(name="AK-47", probability=30),
                        NormalizedLootItem(name="AR-15", probability=30),
                        NormalizedLootItem(name="Glock", probability=40),
                    ],
                ),
                NormalizedRarity(
                    name="Rare",
                    probability=30,
                    items=[
                        NormalizedLootItem(name="Revolver", probability=50),
                        NormalizedLootItem(name="Dagger", probability=50),
                    ],
                ),
                NormalizedRarity(
                    name="Epic",
                    probability=20,
                    items=[
                        NormalizedLootItem(name="Knife", probability=100),
                    ],
                ),
            ],
        )

    def test_builds_endpoints_and_eligible_items_by_rarity(self):
        simulation_state = build_simulation_state(self.config)
        expected_eligible_items_by_rarity = {
            rarity.name: [item for item in rarity.items]
            for rarity in self.config.rarities
        }

        assert (
            simulation_state.eligible_items_by_rarity
            == expected_eligible_items_by_rarity
        )

        assert (
            simulation_state.endpoints["rarities"]["entities"] == self.config.rarities
        )
        assert simulation_state.endpoints["rarities"]["percentages"] == pytest.approx(
            [50, 80, 100]
        )

        assert (
            simulation_state.endpoints["items"]["Common"]["entities"]
            == self.config.rarities[0].items
        )
        assert simulation_state.endpoints["items"]["Rare"][
            "percentages"
        ] == pytest.approx([50, 100])

        assert "Epic" in simulation_state.endpoints["items"]


class TestUpdateState:
    def build_test_config(
        self, is_hard_prevention: bool, rarities: list[NormalizedRarity]
    ):
        return NormalizedSimulationConfig(
            simulation_count=10,
            seed=1234,
            duplicate_mode="hard_prevention"
            if is_hard_prevention
            else "allow_duplicates",
            item_selection_mode="item_probability",
            pulls_per_simulation=20,
            rarities=rarities,
        )

    def setup_method(self):
        self.guaranteed_rarities = [
            NormalizedRarity(
                name="Epic",
                probability=100,
                items=[
                    NormalizedLootItem(name="Knife", probability=100),
                ],
            ),
        ]

        self.equal_rarities = [
            NormalizedRarity(
                name="Rare",
                probability=50,
                items=[
                    NormalizedLootItem(name="Revolver", probability=50),
                    NormalizedLootItem(name="Dagger", probability=50),
                ],
            ),
            NormalizedRarity(
                name="Epic",
                probability=50,
                items=[
                    NormalizedLootItem(name="Knife", probability=70),
                    NormalizedLootItem(name="Hammer", probability=30),
                ],
            ),
        ]

    def test_updates_endpoints_and_eligible_items_hard_prevention_mode(self):
        config = self.build_test_config(True, self.equal_rarities)
        state = build_simulation_state(config)
        rng = generate_rng(config.seed)
        pulled_entities = pull_item(rng, state.endpoints)
        pulled_item = pulled_entities.item
        pulled_rarity = pulled_entities.rarity

        update_state(config=config, state=state, pulled_entities=pulled_entities)

        assert (
            pulled_item.name not in state.eligible_items_by_rarity[pulled_rarity.name]
        )

        for rarity_name, items in state.endpoints["items"].items():
            if rarity_name == pulled_rarity.name:
                assert pulled_item not in items["entities"]
                assert len(items["entities"]) == len(
                    state.eligible_items_by_rarity[rarity_name]
                )

    def test_removes_rarity_when_no_items_remaining_hard_prevention_mode(self):
        config = self.build_test_config(True, self.guaranteed_rarities)
        state = build_simulation_state(config)
        rng = generate_rng(config.seed)
        pulled_entities = pull_item(rng, state.endpoints)
        pulled_rarity = pulled_entities.rarity

        update_state(config, state, pulled_entities)

        assert pulled_rarity.name not in state.endpoints["items"]
        assert not state.endpoints["rarities"]["entities"]
        assert not state.endpoints["rarities"]["percentages"]

        assert not state.eligible_items_by_rarity

    def test_update_pulled_entity_lists(self):
        config = self.build_test_config(True, self.guaranteed_rarities)
        state = build_simulation_state(config)
        rng = generate_rng(config.seed)
        pulled_entities = pull_item(rng, state.endpoints)
        pulled_rarity = pulled_entities.rarity
        pulled_item = pulled_entities.item

        update_state(config, state, pulled_entities)

        assert pulled_rarity in state.pulled_rarities
        assert pulled_item in state.pulled_items

    def test_increment_current_total_pulls(self):
        config = self.build_test_config(True, self.guaranteed_rarities)
        state = build_simulation_state(config)
        rng = generate_rng(config.seed)
        pulled_entities = pull_item(rng, state.endpoints)

        assert state.current_total_pulls == 0

        update_state(config, state, pulled_entities)

        assert state.current_total_pulls == 1


class TestBuildCurrencyMap:
    def setup_method(self):
        self.rarities = [
            NormalizedRarity(
                name="Common",
                probability=50,
                items=[
                    NormalizedLootItem(name="AK-47", probability=30),
                    NormalizedLootItem(name="AR-15", probability=30),
                    NormalizedLootItem(name="Glock", probability=40),
                ],
            ),
            NormalizedRarity(
                name="Rare",
                probability=40,
                items=[
                    NormalizedLootItem(name="AK-47", probability=30),
                    NormalizedLootItem(name="AR-15", probability=30),
                    NormalizedLootItem(name="Glock", probability=40),
                ],
            ),
            NormalizedRarity(
                name="Epic",
                probability=10,
                items=[
                    NormalizedLootItem(name="AK-47", probability=30),
                    NormalizedLootItem(name="AR-15", probability=30),
                    NormalizedLootItem(name="Glock", probability=40),
                ],
            ),
        ]

    def test_builds_currency_map_based_on_rarity_probabilities(self):
        result = build_rarity_currency_map(self.rarities)

        assert result["Common"] == 100
        assert result["Rare"] == 125
        assert result["Epic"] == 500

    def test_calculates_currency_values_using_custom_base_currency(self):
        result = build_rarity_currency_map(self.rarities, 1000)

        assert result["Common"] == 1000
        assert result["Rare"] == 1250
        assert result["Epic"] == 5000

    def test_raises_value_error_when_probability_is_0(self):
        with pytest.raises(ValueError):
            build_rarity_currency_map(
                [NormalizedRarity(name="Common", probability=0, items=[])]
            )


class TestCreatePullResult:
    def setup_method(self):
        self.ak47 = NormalizedLootItem(
            name="AK-47",
            probability=100,
        )

        self.common_rarity = NormalizedRarity(
            name="Common",
            probability=100,
            items=[self.ak47],
        )

        self.currency_map: CurrencyMap = {
            "Common": 100,
            "Rare": 200,
            "Epic": 500,
        }

    def _build_pull_entities(self) -> PulledEntities:
        return PulledEntities(
            rarity=self.common_rarity,
            item=self.ak47,
        )

    def _build_state(
        self,
        *,
        pulled_items: list[NormalizedLootItem] | None = None,
        pulled_rarities: list[NormalizedRarity] | None = None,
        eligible_items_by_rarity: (dict[str, list[NormalizedLootItem]] | None) = None,
    ) -> SimulationState:
        return SimulationState(
            endpoints={
                "rarities": {
                    "entities": [],
                    "percentages": [],
                },
                "items": {},
            },
            eligible_items_by_rarity=eligible_items_by_rarity or {},
            pulled_items=pulled_items or [],
            pulled_rarities=pulled_rarities or [],
        )

    def test_creates_non_duplicate_pull_result(self):
        pulled_entities = self._build_pull_entities()

        state = self._build_state(
            pulled_items=[self.ak47],
            pulled_rarities=[self.common_rarity],
            eligible_items_by_rarity={
                "Common": [self.ak47],
            },
        )

        result = create_pull_result(
            pulled_entities,
            state,
            self.currency_map,
        )

        assert result.rarity == self.common_rarity
        assert result.item == self.ak47
        assert result.is_duplicate is False
        assert result.currency_awarded == 0
        assert result.is_rarity_first_pull is True
        assert result.is_item_first_pull is True
        assert result.is_rarity_complete is False

    def test_creates_duplicate_pull_result_and_awards_currency(self):
        pulled_entities = self._build_pull_entities()

        state = self._build_state(
            pulled_items=[
                self.ak47,
                self.ak47,
            ],
            pulled_rarities=[self.common_rarity],
            eligible_items_by_rarity={
                "Common": [self.ak47],
            },
        )

        result = create_pull_result(
            pulled_entities,
            state,
            self.currency_map,
        )

        assert result.is_duplicate is True
        assert result.currency_awarded == 100

    def test_marks_rarity_as_previously_pulled(self):
        pulled_entities = self._build_pull_entities()

        state = self._build_state(
            pulled_items=[self.ak47],
            pulled_rarities=[
                self.common_rarity,
                self.common_rarity,
            ],
            eligible_items_by_rarity={
                "Common": [self.ak47],
            },
        )

        result = create_pull_result(
            pulled_entities,
            state,
            self.currency_map,
        )

        assert result.is_rarity_first_pull is False

    def test_marks_item_as_previously_pulled(self):
        pulled_entities = self._build_pull_entities()

        state = self._build_state(
            pulled_items=[
                self.ak47,
                self.ak47,
            ],
            pulled_rarities=[self.common_rarity],
            eligible_items_by_rarity={
                "Common": [self.ak47],
            },
        )

        result = create_pull_result(
            pulled_entities,
            state,
            self.currency_map,
        )

        assert result.is_item_first_pull is False

    def test_marks_rarity_as_complete(self):
        pulled_entities = self._build_pull_entities()

        state = self._build_state(
            pulled_items=[self.ak47],
            pulled_rarities=[self.common_rarity],
            eligible_items_by_rarity={},
        )

        result = create_pull_result(
            pulled_entities,
            state,
            self.currency_map,
        )

        assert result.is_rarity_complete is True


from app.simulation.types import PullResult, SimulationTrackingStats
from app.simulation.utils import (
    create_simulation_stats,
    create_simulation_aggregation_stats,
    record_pull,
    update_simulation_aggregation_stats_per_pull,
)


def build_tracking_test_rarities() -> list[NormalizedRarity]:
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


def build_tracking_pull_result(
    rarities: list[NormalizedRarity],
    *,
    rarity_index: int = 0,
    item_index: int = 0,
    is_duplicate: bool = False,
    currency_awarded: int = 0,
    is_rarity_first_pull: bool = False,
    is_item_first_pull: bool = False,
    is_rarity_complete: bool = False,
) -> PullResult:
    rarity = rarities[rarity_index]

    return PullResult(
        rarity=rarity,
        item=rarity.items[item_index],
        is_duplicate=is_duplicate,
        currency_awarded=currency_awarded,
        is_rarity_first_pull=is_rarity_first_pull,
        is_item_first_pull=is_item_first_pull,
        is_rarity_complete=is_rarity_complete,
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
        assert result.median_currency_per_simulation == []
        assert result.mean_currency_per_simulation == []
        assert result.total_currency_per_simulation == []
        assert result.duplicate_amounts_per_simulation == []


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
