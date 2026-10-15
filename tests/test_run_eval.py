import json

from eval.run_eval import BENCHMARK, has_number, load_benchmark, score_answer, score_citations, says_not_enough


def q(kind, rows, type_=None):
    return {"kind": kind, "type": type_ or kind, "expected_rows": rows}


def test_benchmark_has_20_questions_split_10_10():
    qs = load_benchmark()
    assert len(qs) == 20
    assert sum(x["split"] == "tune" for x in qs) == 10
    assert sum(x["split"] == "heldout" for x in qs) == 10
    assert len({x["id"] for x in qs}) == 20


def test_every_question_has_saved_sql_and_result():
    for x in load_benchmark():
        assert x["sql"].strip().upper().startswith("SELECT")
        assert x["expected_rows"]


def test_not_enough_data_cases_present():
    assert sum(x["kind"] == "ned" for x in load_benchmark()) == 5


def test_numbers_match_in_several_formats():
    assert has_number("He is valued at EUR 32 million", 32000000.0)
    assert has_number("32,000,000", 32000000.0)
    assert has_number("1,980 minutes", 1980)
    assert not has_number("19800 minutes", 1980)


def test_ranking_order_and_ties():
    rows = [{"name": "A B", "value": 2700}, {"name": "C D", "value": 2700}, {"name": "E F", "value": 2588}]
    assert score_answer(q("ranking", rows), "1. C D 2. A B 3. E F")
    assert not score_answer(q("ranking", rows), "1. E F 2. A B 3. C D")
    assert not score_answer(q("ranking", rows), "A B and C D only")


def test_ned():
    assert says_not_enough("Not enough data. Missing: xG")
    assert score_answer(q("ned", [{"n": 0}]), "not enough data")
    assert not score_answer(q("ned", [{"n": 0}]), "He scored 9")


def test_value_questions_reject_refusal():
    assert not score_answer(q("value", [{"name": "X", "value": 9}]), "not enough data, nine goals")
    assert score_answer(q("value", [{"name": "X", "value": 9}]), "He scored 9 goals [X, 2025/26]")


def test_citation_check():
    good, total = score_citations("[Kodai Sano, 2025/26] and [Nobody Real, 2025/26] and [Note: A note]",
                                  {("kodai sano", "2025/26")}, {"A note"})
    assert (good, total) == (2, 3)


def test_note_title_that_ends_with_a_season_is_matched_whole():
    good, total = score_citations("[Note: Belgian Pro League attackers, 2025/26]", set(), {"Belgian Pro League attackers, 2025/26"})
    assert (good, total) == (1, 1)


def test_choice_questions():
    q = {"kind": "choice", "options": ["own half", "final third", "balanced"], "expected_option": "final third", "expected_rows": []}
    assert score_answer(q, "Mostly the final third [Vision: X, 2022/23]")
    assert not score_answer(q, "own half and final third")
    assert not score_answer(q, "not enough data")
    yn = {"kind": "choice", "options": ["yes", "no"], "expected_option": "no", "expected_rows": []}
    assert score_answer(yn, "No, few carries")
    assert not score_answer(yn, "not enough data")


def test_vision_split_is_separate_and_has_8_questions():
    assert len(load_benchmark(split="vision")) == 8
    assert len(load_benchmark()) == 20
