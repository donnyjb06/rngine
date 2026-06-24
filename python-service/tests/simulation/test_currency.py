import pytest

from app.domain.models import NormalizedLootItem, NormalizedRarity
from app.simulation.exceptions import InvalidProbabilityError
from app.simulation.util.currency import build_rarity_currency_map


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

    def test_raises_invalid_probability_error_when_probability_is_0(self):
        with pytest.raises(InvalidProbabilityError):
            build_rarity_currency_map(
                [NormalizedRarity(name="Common", probability=0, items=[])]
            )
