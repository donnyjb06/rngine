from bisect import bisect_left
from typing import Sequence

from app.domain.models import NormalizedProbabilityEntity
from app.simulation.exceptions import SimulationEngineExecutionError
from app.simulation.types import EndpointData, T


def normalize_percentages(
    entities: Sequence[T],
):
    total_percentage = sum(entity.probability for entity in entities)
    normalized_entities = []

    if not entities:
        return []

    if total_percentage <= 0:
        raise SimulationEngineExecutionError(
            "Total percentage must be greater than zero to normalize probabilities"
        )

    for entity in entities:
        entity_data = entity.model_dump(exclude={"probability"})
        normalized_percentage = (entity.probability / total_percentage) * 100

        normalized_entities.append(
            NormalizedProbabilityEntity(
                **entity_data, probability=normalized_percentage
            )
        )

    return normalized_entities


def get_next_entity[T](endpoints: EndpointData[T], random_number: float) -> T:
    if len(endpoints["entities"]) != len(endpoints["percentages"]):
        raise SimulationEngineExecutionError(
            "Endpoints data is malformed: entities and percentages length mismatch"
        )

    index = bisect_left(endpoints["percentages"], random_number)
    entity = endpoints["entities"][index]

    return entity
