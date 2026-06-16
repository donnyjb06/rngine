from random import Random

from app.simulation.types import (
    CurrencyMap,
    Endpoints,
    PulledEntities,
    PullResult,
    SimulationState,
)
from app.simulation.util.duplicates import determine_is_duplicate, determine_is_first_pull
from app.simulation.util.probability import get_next_entity
from app.simulation.util.random import get_next_random_value


def pull_item(rng: Random, endpoints: Endpoints) -> PulledEntities:
    random_number_rarity = get_next_random_value(rng)
    random_number_item = get_next_random_value(rng)

    rarity = get_next_entity(endpoints["rarities"], random_number_rarity)
    item = get_next_entity(endpoints["items"][rarity.name], random_number_item)

    return PulledEntities(item=item, rarity=rarity)


def create_pull_result(
    pulled_entities: PulledEntities, state: SimulationState, currency_map: CurrencyMap
) -> PullResult:
    rarity = pulled_entities.rarity
    item = pulled_entities.item
    is_duplicate = determine_is_duplicate(state.pulled_items, item)
    currency_awarded = currency_map[rarity.name] if is_duplicate else 0
    is_rarity_first_pull = determine_is_first_pull(state.pulled_rarities, rarity)
    is_item_first_pull = determine_is_first_pull(state.pulled_items, item)
    is_rarity_complete = rarity.name not in state.eligible_items_by_rarity

    return PullResult(
        rarity=rarity,
        item=item,
        is_duplicate=is_duplicate,
        currency_awarded=currency_awarded,
        is_rarity_first_pull=is_rarity_first_pull,
        is_item_first_pull=is_item_first_pull,
        is_rarity_complete=is_rarity_complete,
    )
