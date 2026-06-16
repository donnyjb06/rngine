import pytest

from app.domain.models import NormalizedProbabilityEntity
from app.simulation.types import EndpointData
from app.simulation.util.endpoints import build_new_endpoint_data, generate_endpoint_data


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
