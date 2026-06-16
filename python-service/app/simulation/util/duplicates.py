from app.domain.models import NormalizedLootItem
from app.simulation.types import T


def determine_is_first_pull[T](pulled_entities: list[T], entity: T) -> bool:
    return entity not in pulled_entities[:-1]


def determine_is_duplicate(
    pulled_items: list[NormalizedLootItem], item: NormalizedLootItem
) -> bool:
    return item in pulled_items[:-1] and item == pulled_items[-1]
