import pandas as pd

from rag.vision.common import norm, season_of
from rag.vision.summarise import tag_row


def acts(rows):
    return pd.DataFrame(rows, columns=["type", "x", "y", "end_x", "end_y", "outcome", "xg", "length", "is_goal"])


def test_season_label_follows_start_year():
    assert season_of("2022-11-20") == "2022/23"
    assert season_of("2024-06-14") == "2023/24"
    assert season_of("2024-07-14") == "2024/25"


def test_norm_strips_accents():
    assert norm("Nicolò Tresoldi") == "nicolo tresoldi"


def test_tags_from_event_rows():
    passes = [["Pass", 20, 40, 45, 40, "Complete", None, 25.0, 0]] * 30 + [["Pass", 30, 40, 55, 40, "Complete", None, 25.0, 0]] * 20
    t = tag_row(acts(passes), n_matches=2)
    assert t["tag_passing_territory"] == "mostly_own_half"
    assert t["tag_pass_direction"] == "mostly_forward"
    assert t["tag_pass_length"] == "long"
    assert t["tag_shooting"] == "too_few_shots"


def test_shot_distance_tag():
    shots = [["Shot", 108, 40, 120, 40, "Goal", 0.3, None, 1], ["Shot", 110, 38, 120, 40, "Saved", 0.2, None, 0]]
    assert tag_row(acts(shots), 1)["tag_shooting"] == "shots_from_close"
    far = [["Shot", 90, 40, 120, 40, "Off T", 0.03, None, 0], ["Shot", 92, 30, 120, 40, "Off T", 0.03, None, 0]]
    assert tag_row(acts(far), 1)["tag_shooting"] == "shots_from_range"


def test_carry_tag():
    carries = [["Carry", 70, 40, 85, 40, "Carry", None, None, 0]] * 4
    assert tag_row(acts(carries), n_matches=2)["tag_carrying"] == "carries_into_final_third"
