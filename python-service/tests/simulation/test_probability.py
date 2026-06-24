import pytest

from app.domain.models import NormalizedProbabilityEntity
from app.simulation.exceptions import SimulationEngineExecutionError
from app.simulation.types import EndpointData
from app.simulation.util.probability import get_next_entity, normalize_percentages


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
            SimulationEngineExecutionError,
            match="entities and percentages length mismatch",
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
            SimulationEngineExecutionError,
            match="Total percentage must be greater than zero",
        ):
            normalize_percentages(entities)
