from typing import Sequence

from app.domain.models import NormalizedProbabilityEntity
from app.simulation.types import EndpointData, T
from app.simulation.util.probability import normalize_percentages


def generate_endpoint_data(
    probability_entities: Sequence[NormalizedProbabilityEntity],
) -> EndpointData:
    endpoints: EndpointData = {"entities": [], "percentages": []}
    total_percentage = 0.0
    for entity in probability_entities:
        total_percentage += entity.probability
        endpoints["entities"].append(entity)
        endpoints["percentages"].append(total_percentage)
    return endpoints


def build_new_endpoint_data(
    removed_entity: T,
    entities: Sequence[T],
):
    filtered_entities = [
        entity for entity in entities if entity.name != removed_entity.name
    ]

    eligible_entities = normalize_percentages(filtered_entities)

    return generate_endpoint_data(eligible_entities)
