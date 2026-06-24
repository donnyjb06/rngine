from typing import Sequence
from math import isclose
from app.domain.models import RawLootItem, RawRarity
from app.simulation.exceptions import (
    InvalidProbabilityError,
    InvalidWeightError,
    SimulationConfigError,
)
from .constants import MAX_PULL_AMOUNT, PERCENT_TOLERANCE, PERCENT_TOTAL
from app.domain import (
    RawSimulationConfig,
    NormalizedSimulationConfig,
    NormalizedRarity,
    NormalizedLootItem,
)


def validate_weight(rarities: list[RawRarity], item_selection_mode: str) -> None:
    for rarity in rarities:
        if rarity.weight is None or rarity.weight < 0:
            raise InvalidWeightError(
                f"Rarity {rarity.name} must have a non-negative weight"
            )

        if item_selection_mode == "item_probability":
            for item in rarity.items:
                if item.weight is None or item.weight < 0:
                    raise InvalidWeightError(
                        f"Item {item.name} in rarity {rarity.name} must have a non-negative weight"
                    )


def validate_config(config: RawSimulationConfig) -> None:
    if config.simulation_count <= 0:
        raise SimulationConfigError("simulation_count must be greater than 0")

    if config.simulation_count * config.pulls_per_simulation > MAX_PULL_AMOUNT:
        raise SimulationConfigError(
            f"simulation_count must not exceed {MAX_PULL_AMOUNT}"
        )

    if config.duplicate_mode == "hard_prevention":
        for rarity in config.rarities:
            if len(rarity.items) < config.pulls_per_simulation:
                raise SimulationConfigError(
                    f"Not enough items in rarity {rarity.name} to prevent duplicates"
                )

    if config.pulls_per_simulation <= 0:
        raise SimulationConfigError("pulls_per_simulation must be greater than 0")

    if config.probability_mode == "weight":
        validate_weight(config.rarities, config.item_selection_mode)
        return

    for rarity in config.rarities:
        if rarity.probability is not None and (
            rarity.probability < 0 or rarity.probability > 100
        ):
            raise InvalidProbabilityError(
                f"Rarity {rarity.name} has invalid probability {rarity.probability}"
            )

        total_item_probability = sum(
            item.probability for item in rarity.items if item.probability is not None
        )

        if not isclose(
            total_item_probability,
            PERCENT_TOTAL,
            abs_tol=PERCENT_TOLERANCE,
        ):
            raise InvalidProbabilityError(
                f"Total item probabilities in rarity {rarity.name} must not exceed 100%"
            )

        for item in rarity.items:
            if item.probability is not None and (
                item.probability < 0 or item.probability > 100
            ):
                raise InvalidProbabilityError(
                    f"Item {item.name} in rarity {rarity.name} has invalid probability {item.probability}"
                )


def validate_percentages(config: NormalizedSimulationConfig) -> None:
    total_rarity_probability = sum(
        rarity.probability
        for rarity in config.rarities
        if rarity.probability is not None
    )

    if not isclose(
        total_rarity_probability,
        PERCENT_TOTAL,
        abs_tol=PERCENT_TOLERANCE,
    ):
        raise InvalidProbabilityError("Total rarity probabilities must not exceed 100%")

    for rarity in config.rarities:
        if rarity.probability is not None and (
            rarity.probability < 0 or rarity.probability > 100
        ):
            raise InvalidProbabilityError(
                f"Rarity {rarity.name} has invalid probability {rarity.probability}"
            )

        total_item_probability = sum(
            item.probability for item in rarity.items if item.probability is not None
        )

        if not isclose(
            total_item_probability,
            PERCENT_TOTAL,
            abs_tol=PERCENT_TOLERANCE,
        ):
            raise InvalidProbabilityError(
                f"Total item probabilities in rarity {rarity.name} must not exceed 100%"
            )

        for item in rarity.items:
            if item.probability is not None and (
                item.probability < 0 or item.probability > 100
            ):
                raise InvalidProbabilityError(
                    f"Item {item.name} in rarity {rarity.name} has invalid probability {item.probability}"
                )


def getTotalWeight(entities: Sequence[RawRarity | RawLootItem]) -> float:
    total_weight = 0.0

    for entity in entities:
        if entity.weight is not None:
            if entity.weight <= 0:
                raise InvalidWeightError(
                    f"Entity {entity.name} has invalid weight {entity.weight}"
                )

            total_weight += entity.weight

    return total_weight


def require_weight(entity: RawRarity | RawLootItem) -> float:
    if entity.weight is None:
        raise InvalidWeightError(f"Entity {entity.name} is missing weight")

    elif entity.weight <= 0:
        raise InvalidWeightError(
            f"Entity {entity.name} has invalid weight {entity.weight}"
        )

    return entity.weight


def normalize_items_for_rarity(
    rarity: RawRarity, item_selection_mode: str, probability_mode: str
) -> list[NormalizedLootItem]:
    total_weight = getTotalWeight(rarity.items)
    items = []
    if not rarity.items:
        raise SimulationConfigError("Rarity {rarity.name} must have at least one item")

    if (
        total_weight == 0
        and probability_mode == "weight"
        and not item_selection_mode == "equal_chance"
    ):
        raise InvalidWeightError(
            f"Total weight for items in rarity {rarity.name} cannot be zero for weight-based probability mode"
        )

    for item in rarity.items:
        if item_selection_mode == "equal_chance":
            probability = 100 / len(rarity.items)

        elif probability_mode == "weight":
            probability = (require_weight(item) / total_weight) * 100

        else:
            if item.probability is None:
                raise InvalidProbabilityError(
                    f"Item {item.name} in rarity {rarity.name} must have a probability if probability_mode is set to percentage"
                )

            probability = item.probability

        item_data = item.model_dump(exclude={"weight", "probability"})
        normalized_item = NormalizedLootItem(probability=probability, **item_data)

        items.append(normalized_item)

    return items


def normalize_rarity(
    rarity: RawRarity,
    total_rarity_weight: float | None,
    item_selection_mode: str,
    probability_mode: str,
) -> NormalizedRarity:
    if probability_mode == "weight":
        if total_rarity_weight is None:
            raise InvalidWeightError(
                "Total rarity weight is required for weight-based probability mode"
            )

        probability = (require_weight(rarity) / total_rarity_weight) * 100

    else:
        if rarity.probability is None:
            raise InvalidProbabilityError(
                "probability must exist if probability_mode is set to percentage"
            )

        probability = rarity.probability

    rarity_data = rarity.model_dump(exclude={"items", "weight", "probability"})
    return NormalizedRarity(
        items=normalize_items_for_rarity(rarity, item_selection_mode, probability_mode),
        probability=probability,
        **rarity_data,
    )


def normalize_config(config: RawSimulationConfig) -> NormalizedSimulationConfig:
    total_rarity_weight = getTotalWeight(config.rarities)

    rarities = [
        normalize_rarity(
            rarity,
            total_rarity_weight,
            config.item_selection_mode,
            probability_mode=config.probability_mode,
        )
        for rarity in config.rarities
    ]

    config_data = config.model_dump(exclude={"rarities", "probability_mode"})

    return NormalizedSimulationConfig(**config_data, rarities=rarities)
