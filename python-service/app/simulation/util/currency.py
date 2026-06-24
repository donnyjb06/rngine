from app.domain.models import NormalizedRarity
from app.simulation.constants import BASE_CURRENCY
from app.simulation.exceptions import InvalidProbabilityError


def build_rarity_currency_map(
    entities: list[NormalizedRarity], base_currency: int = BASE_CURRENCY
) -> dict[str, int]:
    max_probability = max(entity.probability for entity in entities)
    currency_map = {}

    for entity in entities:
        if max_probability <= 0 or entity.probability <= 0:
            raise InvalidProbabilityError(
                "Probabilities must be greater than zero to calculate currency values"
            )

        currency_map[entity.name] = round(
            base_currency * (max_probability / entity.probability)
        )

    return currency_map
