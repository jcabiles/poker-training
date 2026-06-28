from app.domain.srs import quality_from_correctness, sm2


def test_quality_mapping():
    assert quality_from_correctness("optimal") == 5
    assert quality_from_correctness("acceptable") == 4
    assert quality_from_correctness("mistake") == 2
    assert quality_from_correctness("blunder") == 0
    assert quality_from_correctness(None) == 0


def test_failed_resets_interval():
    ease, interval, reps = sm2(2.5, 30, 5, quality=0)
    assert reps == 0
    assert interval == 1
    assert ease >= 1.3


def test_success_grows_interval():
    ease, interval, reps = sm2(2.5, 0, 0, quality=5)
    assert (interval, reps) == (1, 1)
    ease, interval, reps = sm2(ease, interval, reps, quality=5)
    assert (interval, reps) == (6, 2)
    ease, interval, reps = sm2(ease, interval, reps, quality=5)
    assert interval > 6 and reps == 3


def test_ease_floor():
    ease, _, _ = sm2(1.3, 5, 3, quality=0)
    assert ease >= 1.3
