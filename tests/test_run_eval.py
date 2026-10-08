import json

from eval.run_eval import BENCHMARK, load_benchmark


def test_every_question_has_sql_and_type():
    data = json.loads(BENCHMARK.read_text())
    for q in data["questions"]:
        assert q["sql"].strip(), f"{q['id']} has no SQL"
        assert q["type"] in {"single_fact", "filtered_ranking", "profile_match", "comparison", "not_enough_data"}


def test_unscored_example_is_skipped():
    assert all(q["scored"] for q in load_benchmark())
