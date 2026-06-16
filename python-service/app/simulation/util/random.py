from random import Random


def generate_rng(seed: int | None) -> Random:
    rng = Random(seed)
    return rng


def get_next_random_value(rng: Random) -> float:
    return rng.uniform(0, 100)
