from anonymator.model import Entity
from anonymator.dedup import detect_unique

def fake_detect(value):
    # détecte "Zoé" comme PERSON où qu'elle soit
    return [Entity("PERSON", "Zoé", i, i + 3, "ner", 1.0)
            for i in range(len(value)) if value[i:i + 3] == "Zoé"]

def test_detects_each_unique_value_once():
    calls = []
    def counting(value):
        calls.append(value)
        return fake_detect(value)
    values = ["Zoé Martin", "Zoé Martin", "Banque X"]
    result = detect_unique(values, counting)
    # 2 valeurs uniques → 2 appels seulement
    assert sorted(calls) == ["Banque X", "Zoé Martin"]
    assert result["Zoé Martin"][0].type == "PERSON"
    assert result["Banque X"] == []
