from random import Random
from app.domain import NormalizedSimulationConfig
from app.simulation import (
    build_simulation_state,
    create_pull_result,
    pull_item,
    update_state,
    record_pull,
)
from .types import (
    CurrencyMap,
    DuplicationConfig,
    SimulationTrackingStats,
)


def run_simulation(
    config: NormalizedSimulationConfig,
    tracking_stats: SimulationTrackingStats,
    currency_map: CurrencyMap,
    rng: Random,
):
    state = build_simulation_state(config)

    for _ in range(config.pulls_per_simulation):
        pulled_entities = pull_item(rng, state.endpoints)
        update_state(config, state, pulled_entities)
        pull_result = create_pull_result(pulled_entities, state, currency_map)
        duplication_config = DuplicationConfig(
            is_hard_prevention=config.duplicate_mode == "hard_prevention",
            are_duplicate_possible=config.duplicate_mode != "hard_prevention",
        )

        record_pull(
            tracking_stats, pull_result, duplication_config, state.current_total_pulls
        )

        if not state.eligible_items_by_rarity:
            break

    """
    simulation_state = build_simulation_state(config, rng)
        create_endpoints
        create eligible_items_by_rarity
        RETURN new SimulationState object

    FOR each pull in config.pulls_per_simulation:
        pull_item(rng)
            get next random number
            get next rarity
            get next item

            RETURN item, rarity

        update_state(config, state, pulled item, pulled rarity)
            if hard_prevention
            update endpoints
            update eligible_items_by_rarity

            increment current total pulls


        create pull results(pulled_item, pulled_rarity, state, currency_map)
            pull_result = PullResult(
                is_item_first_pull = item not in pulled items
                is_rarity_first_pull = item not in pulled rarities
                rarity_name = rarity.name
                item.name = item.name
                currency_awarded = currency value of pulled rarity name key if duplicate currency else 0
                is_rarity_complete = items list for rarity in eligible_items_by_rarity is empty
                is_duplicate = true if allow duplicate or duplicate currency else false
                                     )

            add rarity to pulled rarities
            add item to pulled items

            return pull_result

        record_pull
            update_simulation_stats(pull_result, simulation_stats, config, state)
                award global, simulation item, simulation rarity currency
                increment global, simulation item, simulation rarity duplicates if is duplicate

                increment pulled item and rarity pull counts

            update_simulation_aggregation_stats_per_pull()
                if item first pull
                    append current total pulls to pulled item pulls until entity list

                if rarity first pull
                    append current total pulls to pulled rarity pulls until entity list

                if hard_prevention
                    if rarity complete
                        append current total pulls to pulled rarity pulls until complete list


    """
