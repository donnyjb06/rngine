from app.domain.models import NormalizedLootItem, NormalizedRarity
from app.simulation.types import PullResult


def build_tracking_test_rarities() -> list[NormalizedRarity]:
    return [
        NormalizedRarity(
            name="Common",
            probability=80,
            items=[
                NormalizedLootItem(name="AK-47", probability=70),
                NormalizedLootItem(name="Glock", probability=30),
            ],
        ),
        NormalizedRarity(
            name="Rare",
            probability=20,
            items=[
                NormalizedLootItem(name="Knife", probability=100),
            ],
        ),
    ]


def build_tracking_pull_result(
    rarities: list[NormalizedRarity],
    *,
    rarity_index: int = 0,
    item_index: int = 0,
    is_duplicate: bool = False,
    currency_awarded: int = 0,
    is_rarity_first_pull: bool = False,
    is_item_first_pull: bool = False,
    is_rarity_complete: bool = False,
) -> PullResult:
    rarity = rarities[rarity_index]

    return PullResult(
        rarity=rarity,
        item=rarity.items[item_index],
        is_duplicate=is_duplicate,
        currency_awarded=currency_awarded,
        is_rarity_first_pull=is_rarity_first_pull,
        is_item_first_pull=is_item_first_pull,
        is_rarity_complete=is_rarity_complete,
    )
