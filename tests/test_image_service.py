from Backend.image_service import name_match_score, normalize_text


def test_normalize_text():
    assert normalize_text(" Café Köln! ") == "cafe koln"


def test_name_match_score_exact():
    assert name_match_score("Central Cafe", "File: Central Cafe.jpg") == 1.0


def test_name_match_score_partial():
    score = name_match_score("Central Cafe", "File: Central Park Cafe.jpg")
    assert 0.5 <= score < 1.0


def test_name_match_score_empty():
    assert name_match_score("", "File: image.jpg") == 0.0
