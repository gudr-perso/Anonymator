from unittest.mock import patch
from anonymator.brand import active_brand, reset_brand


def teardown_function():
    reset_brand()


def test_cap_entry_locks_cap_then_calls_main():
    import anonymator.brands.cap as entry
    with patch("anonymator.brands.cap.main", return_value=0) as m:
        rc = entry.run()
    assert rc == 0
    assert m.called
    assert active_brand().key == "cap"


def test_cuma_entry_locks_cuma_then_calls_main():
    import anonymator.brands.cuma as entry
    with patch("anonymator.brands.cuma.main", return_value=0) as m:
        rc = entry.run()
    assert rc == 0
    assert m.called
    assert active_brand().key == "cuma"
