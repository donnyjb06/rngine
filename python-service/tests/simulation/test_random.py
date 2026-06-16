from random import Random

from app.simulation.util.random import generate_rng, get_next_random_value


class TestGenerateRng:
    def test_returns_random_instance(self):
        rng = generate_rng(123)

        assert isinstance(rng, Random)

    def test_same_seed_produces_same_sequence(self):
        rng_one = generate_rng(123)
        rng_two = generate_rng(123)

        assert rng_one.random() == rng_two.random()
        assert rng_one.random() == rng_two.random()

    def test_different_seeds_produce_different_sequence(self):
        rng_one = generate_rng(123)
        rng_two = generate_rng(456)

        assert rng_one.random() != rng_two.random()


class TestGetNextRandomValue:
    def test_returns_value_between_0_and_100(self):
        rng = generate_rng(123)

        value = get_next_random_value(rng)

        assert 0 <= value <= 100

    def test_same_seed_produces_same_next_random_value(self):
        rng_one = generate_rng(123)
        rng_two = generate_rng(123)

        assert get_next_random_value(rng_one) == get_next_random_value(rng_two)
