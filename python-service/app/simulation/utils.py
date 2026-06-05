from random import Random
from typing import Sequence
from .constants import BASE_CURRENCY
from bisect import bisect_left
from app.domain.models import (
    NormalizedLootItem,
    NormalizedProbabilityEntity,
    NormalizedRarity,
    NormalizedSimulationConfig,
)
from app.simulation.types import (
    AggregationProbabilityEntityStats,
    AggregationRarityStats,
    CurrencyMap,
    DuplicationConfig,
    EndpointData,
    Endpoints,
    GlobalStats,
    ProbabilityEntityStats,
    PullResult,
    PulledEntities,
    SimulationAggregationStats,
    SimulationBatchStats,
    SimulationState,
    T,
    SimulationStats,
    ItemStats,
    SimulationTrackingStats,
)


def generate_rng(seed: int | None) -> Random:
    rng = Random(seed)
    return rng


def get_next_random_value(rng: Random) -> float:
    return rng.uniform(0, 100)


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


def get_next_entity[T](endpoints: EndpointData[T], random_number: float) -> T:
    if len(endpoints["entities"]) != len(endpoints["percentages"]):
        raise ValueError(
            "Endpoints data is malformed: entities and percentages length mismatch"
        )

    index = bisect_left(endpoints["percentages"], random_number)
    entity = endpoints["entities"][index]

    return entity


def build_new_endpoint_data(
    removed_entity: T,
    entities: Sequence[T],
):
    filtered_entities = [
        entity for entity in entities if entity.name != removed_entity.name
    ]

    eligible_entities = normalize_percentages(filtered_entities)

    return generate_endpoint_data(eligible_entities)


def normalize_percentages(
    entities: Sequence[T],
):
    total_percentage = sum(entity.probability for entity in entities)
    normalized_entities = []

    if not entities:
        return []

    if total_percentage <= 0:
        raise ValueError(
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


def build_rarity_currency_map(
    entities: list[NormalizedRarity], base_currency: int = BASE_CURRENCY
) -> dict[str, int]:
    max_probability = max(entity.probability for entity in entities)
    currency_map = {}

    for entity in entities:
        if max_probability <= 0 or entity.probability <= 0:
            raise ValueError(
                "Probabilities must be greater than zero to calculate currency values"
            )

        currency_map[entity.name] = round(
            base_currency * (max_probability / entity.probability)
        )

    return currency_map


def pull_item(rng: Random, endpoints: Endpoints) -> PulledEntities:
    random_number = get_next_random_value(rng)
    rarity = get_next_entity(endpoints["rarities"], random_number)
    item = get_next_entity(endpoints["items"][rarity.name], random_number)

    return PulledEntities(item=item, rarity=rarity)


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


def determine_is_first_pull[T](pulled_entities: list[T], entity: T) -> bool:
    return entity not in pulled_entities[:-1]


def determine_is_duplicate(
    pulled_items: list[NormalizedLootItem], item: NormalizedLootItem
) -> bool:
    return item in pulled_items[:-1] and item == pulled_items[-1]


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


def create_rarity_stats(rarities: list[NormalizedRarity]) -> ProbabilityEntityStats:
    initial_counts = {rarity.name: 0 for rarity in rarities}

    return ProbabilityEntityStats(
        pull_counts=initial_counts.copy(), currency_amounts=initial_counts.copy()
    )


def create_item_stats(items: list[NormalizedLootItem]) -> ItemStats:
    initial_counts = {item.name: 0 for item in items}

    return ItemStats(
        pull_counts=initial_counts.copy(),
        currency_amounts=initial_counts.copy(),
        duplicate_amounts=initial_counts.copy(),
    )


def create_simulation_stats(rarities: list[NormalizedRarity]) -> SimulationStats:
    rarity_stats = create_rarity_stats(rarities)
    item_stats = create_item_stats(
        [item for rarity in rarities for item in rarity.items]
    )

    return SimulationStats(rarity_stats=rarity_stats, item_stats=item_stats)


def initialize_empty_lists(
    entities: Sequence[NormalizedProbabilityEntity],
) -> dict[str, list[int]]:
    return {entity.name: [] for entity in entities}


def create_item_aggregation_stats(
    items: list[NormalizedLootItem],
) -> AggregationProbabilityEntityStats:

    return AggregationProbabilityEntityStats(
        pulls_until_entity=initialize_empty_lists(items)
    )


def create_rarity_aggregation_stats(
    rarities: list[NormalizedRarity],
) -> AggregationRarityStats:

    return AggregationRarityStats(
        pulls_until_entity=initialize_empty_lists(rarities),
        pulls_until_completion=initialize_empty_lists(rarities),
    )


def create_simulation_aggregation_stats(
    rarities: list[NormalizedRarity],
) -> SimulationAggregationStats:
    item_stats = create_item_aggregation_stats(
        [item for rarity in rarities for item in rarity.items]
    )
    rarity_stats = create_rarity_aggregation_stats(rarities)
    return SimulationAggregationStats(item_stats=item_stats, rarity_stats=rarity_stats)


def record_pull(
    stats: SimulationTrackingStats,
    pull_result,
    duplication_config: DuplicationConfig,
    current_total_pulls: int,
):
    update_simulation_stats(pull_result, duplication_config, stats["simulation"])
    update_simulation_aggregation_stats_per_pull(
        pull_result, current_total_pulls, stats["aggregation"]
    )


def update_simulation_stats(
    pull_result: PullResult,
    duplication_config: DuplicationConfig,
    stats: SimulationStats,
):
    rarity_name = pull_result.rarity.name
    item_name = pull_result.item.name

    stats.total_currency += pull_result.currency_awarded
    stats.rarity_stats.currency_amounts[rarity_name] += pull_result.currency_awarded
    stats.item_stats.currency_amounts[item_name] += pull_result.currency_awarded

    if pull_result.is_duplicate:
        stats.total_duplicates += 1

        if duplication_config["are_duplicate_possible"]:
            stats.item_stats.duplicate_amounts[item_name] += 1

    stats.rarity_stats.pull_counts[rarity_name] += 1
    stats.item_stats.pull_counts[item_name] += 1


def update_simulation_aggregation_stats_per_pull(
    pull_result: PullResult,
    current_total_pulls: int,
    stats: SimulationAggregationStats,
):
    rarity_name = pull_result.rarity.name
    item_name = pull_result.item.name

    if pull_result.is_item_first_pull:
        stats.item_stats.pulls_until_entity[item_name].append(current_total_pulls)

    if pull_result.is_rarity_first_pull:
        stats.rarity_stats.pulls_until_entity[rarity_name].append(current_total_pulls)

    if pull_result.is_rarity_complete:
        stats.rarity_stats.pulls_until_completion[rarity_name].append(
            current_total_pulls
        )
