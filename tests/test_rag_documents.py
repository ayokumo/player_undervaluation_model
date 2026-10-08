import pytest

from rag.documents import MIN_MINUTES, build_profile, is_indexable


def winger_row(**overrides):
    row = {
        "player_id": 123,
        "name": "Test Winger",
        "season": "2024/25",
        "position_group": "winger",
        "league": "NL1",
        "club": "Test FC",
        "age": 21,
        "minutes": 2100,
        "goals_p90": 0.31,
        "key_passes_p90": 2.4,
    }
    row.update(overrides)
    return row


def test_profile_contains_identity_and_stats():
    doc = build_profile(winger_row())
    assert doc.doc_id == "123_2024/25"
    assert "Test Winger" in doc.text
    assert "key_passes_p90: 2.40" in doc.text


def test_missing_stat_shown_as_na_not_zero():
    doc = build_profile(winger_row())
    assert "xg_p90: n/a" in doc.text


def test_metadata_has_filter_fields():
    meta = build_profile(winger_row()).metadata
    for key in ["position_group", "league", "age", "minutes"]:
        assert key in meta


def test_missing_required_field_raises():
    with pytest.raises(ValueError):
        build_profile(winger_row(name=None))


def test_unknown_position_raises():
    with pytest.raises(ValueError):
        build_profile(winger_row(position_group="libero"))


def test_minutes_threshold():
    assert is_indexable({"minutes": MIN_MINUTES})
    assert not is_indexable({"minutes": MIN_MINUTES - 1})
    assert not is_indexable({"minutes": None})
