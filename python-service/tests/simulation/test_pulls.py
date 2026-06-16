from app.domain.models import NormalizedLootItem, NormalizedRarity
from app.simulation.types import CurrencyMap, Endpoints, PulledEntities, SimulationState
from app.simulation.util.endpoints import generate_endpoint_data
from app.simulation.util.pulls import create_pull_result, pull_item
from app.simulation.util.random import generate_rng


def build_test_endpoints(rarities: list[NormalizedRarity]) -> Endpoints:
    return {
        "rarities": generate_endpoint_data((rarities)),
        "items": {
            rarity.name: generate_endpoint_data(rarity.items) for rarity in rarities
        },
    }


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
