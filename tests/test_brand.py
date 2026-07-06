from anonymator.brand import (
    Brand, BRANDS, lock_brand, reset_brand, active_brand, is_locked, build_target,
)


def teardown_function():
    reset_brand()   # isole l'état global entre les tests


def test_default_is_dev_unlocked():
    reset_brand()
    b = active_brand()
    assert b.key == "dev"
    assert b.locked is False
    assert is_locked() is False
    assert b.product_name == "Anonymator"
    assert b.theme is None


def test_lock_cap_forces_theme_and_name():
    lock_brand("cap")
    b = active_brand()
    assert b.theme == "cap"
    assert b.product_name == "CAP'nonyme"
    assert b.exe_name == "capnonyme"
    assert is_locked() is True


def test_lock_cuma_forces_theme_and_name():
    lock_brand("cuma")
    b = active_brand()
    assert b.theme == "cuma"
    assert b.product_name == "Cum'Anonyme"
    assert b.exe_name == "cumanonyme"
    assert is_locked() is True


def test_reset_returns_to_dev():
    lock_brand("cap")
    reset_brand()
    assert active_brand().key == "dev"


def test_build_target_maps_brand_to_entry_and_name():
    assert build_target("cap") == (
        "anonymator/brands/cap.py", "capnonyme", "anonymator.ico")
    assert build_target("cuma") == (
        "anonymator/brands/cuma.py", "cumanonyme", "anonymator.ico")


def test_build_target_unknown_falls_back_to_dev():
    assert build_target("dev") == (
        "anonymator/__main__.py", "anonymator", "anonymator.ico")
    assert build_target("nimportequoi") == (
        "anonymator/__main__.py", "anonymator", "anonymator.ico")
