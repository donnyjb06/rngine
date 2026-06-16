from app.domain.models import NormalizedSimulationConfig
from app.simulation.types import Endpoints, PulledEntities, SimulationState
from app.simulation.util.endpoints import build_new_endpoint_data, generate_endpoint_data


def build_simulation_state(config: NormalizedSimulationConfig) -> SimulationState:
    endpoints: Endpoints = {
        "rarities": generate_endpoint_data(config.rarities),
        "items": {
            rarity.name: generate_endpoint_data(rarity.items)
            for rarity in config.rarities
        },
    }

    eligible_items_by_rarity = {
        rarity.name: [item for item in rarity.items] for rarity in config.rarities
    }

    return SimulationState(
        endpoints=endpoints, eligible_items_by_rarity=eligible_items_by_rarity
    )


def handle_hard_prevention_state_update(
    state: SimulationState, pulled_entities: PulledEntities
):
    rarity = pulled_entities.rarity

    new_item_endpoints = build_new_endpoint_data(
        pulled_entities.item,
        state.endpoints["items"][rarity.name]["entities"],
    )

    if not new_item_endpoints["entities"]:
        new_rarity_endpoints = build_new_endpoint_data(
            rarity, state.endpoints["rarities"]["entities"]
        )
        state.endpoints["rarities"] = new_rarity_endpoints
        state.endpoints["items"].pop(rarity.name, None)
        state.eligible_items_by_rarity.pop(rarity.name, None)

    else:
        state.endpoints["items"][pulled_entities.rarity.name] = new_item_endpoints
        state.eligible_items_by_rarity[rarity.name] = new_item_endpoints["entities"]


def update_pulled_items(state: SimulationState, pulled_entities: PulledEntities):
    rarity = pulled_entities.rarity
    item = pulled_entities.item

    state.pulled_items.append(item)
    state.pulled_rarities.append(rarity)


def update_state(
    config: NormalizedSimulationConfig,
    state: SimulationState,
    pulled_entities: PulledEntities,
) -> None:
    if config.duplicate_mode == "hard_prevention":
        handle_hard_prevention_state_update(state, pulled_entities)

    update_pulled_items(state, pulled_entities)
    state.current_total_pulls += 1
