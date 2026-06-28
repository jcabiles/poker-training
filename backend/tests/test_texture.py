from app.domain.texture import classify


def test_dry_rainbow_unpaired_anchor():
    t = classify(["As", "Kd", "2c"])
    assert t.wetness == "dry"
    assert t.suitedness == "rainbow"
    assert t.pairing == "unpaired"
    assert t.connectedness == "disconnected"
    assert t.high_card == "A"
    assert t.high_board is True


def test_wet_monotone_connected_anchor():
    t = classify(["9h", "8h", "7h"])
    assert t.wetness == "wet"
    assert t.suitedness == "monotone"
    assert t.connectedness == "connected"
    assert t.pairing == "unpaired"


def test_paired_board():
    t = classify(["Kh", "Kd", "7c"])
    assert t.pairing == "paired"


def test_texture_class_is_board_independent():
    # Two different dry, rainbow, disconnected, unpaired flops share a class.
    a = classify(["As", "Kd", "2c"]).texture_class
    b = classify(["Ah", "Qd", "3c"]).texture_class
    assert a == b


def test_needs_three_cards():
    try:
        classify(["As", "Kd"])
    except ValueError:
        return
    raise AssertionError("expected ValueError for a 2-card board")
