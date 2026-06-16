import pytest

from app.domain.models import (
    NormalizedLootItem,
    NormalizedRarity,
    NormalizedSimulationConfig,
)
from app.simulation.util.pulls import pull_item
from app.simulation.util.random import generate_rng
from app.simulation.util.state import build_simulation_state, update_state


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
