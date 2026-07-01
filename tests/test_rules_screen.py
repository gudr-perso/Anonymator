from anonymator.ui.rules_screen import RulesScreen
from anonymator.user_rules import UserRules


def test_add_and_remove_rule(qtbot, tmp_path):
    rules_path = tmp_path / "user_rules.json"
    UserRules([]).save(rules_path)
    applied = []
    s = RulesScreen(rules_path=rules_path,
                    on_apply=lambda: applied.append(True),
                    on_back=lambda: None)
    qtbot.addWidget(s)
    s.add_rule(mode="simple", pattern="FACT#######", action="keep", note="factures")
    assert s.user_rules.keep_matches("FACT1234567")
    assert applied  # on_apply déclenché → MainWindow reconstruit le référentiel
    rule = s.user_rules.rules[0]
    s.remove_rule(rule)
    assert not s.user_rules.keep_matches("FACT1234567")


def test_invalid_regex_shows_error(qtbot, tmp_path):
    rules_path = tmp_path / "user_rules.json"
    UserRules([]).save(rules_path)
    s = RulesScreen(rules_path=rules_path, on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(s)
    s.add_rule(mode="regex", pattern="[unclosed", action="mask", note="")
    assert "invalide" in s.rule_error.text().lower()
    assert not s.user_rules.rules


def test_rule_persisted_to_disk(qtbot, tmp_path):
    # reprend la couverture de test_ui_smoke::test_settings_screen_adds_and_persists_rule
    rules_path = tmp_path / "user_rules.json"
    UserRules([]).save(rules_path)
    s = RulesScreen(rules_path=rules_path, on_apply=lambda: None, on_back=lambda: None)
    qtbot.addWidget(s)
    s.add_rule(mode="simple", pattern="A#######", action="keep", note="codes internes")
    reloaded = UserRules.load(rules_path)
    assert reloaded.keep_matches("A0000015")
    assert s.rules_path_label.text().find("user_rules.json") != -1
