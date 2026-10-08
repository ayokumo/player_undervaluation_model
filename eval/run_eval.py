"""Step 5 (planned): run the 20 question benchmark and write eval/results.md.

Plan:
* For each scored question in eval/benchmark.json: rerun its SQL to get the
  expected answer and citations, then ask rag.chain.answer the question.
* Metrics:
    answer accuracy      = answers matching the SQL result
    citation accuracy    = cited player seasons that are in the SQL result
    not enough data      = said "not enough data" on questions of type not_enough_data
* Write a dated table to eval/results.md. Never edit results.md by hand.
"""

import json
from pathlib import Path

BENCHMARK = Path(__file__).parent / "benchmark.json"


def load_benchmark(path: Path = BENCHMARK) -> list[dict]:
    """Load only the questions marked scored=true."""
    data = json.loads(path.read_text())
    return [q for q in data["questions"] if q.get("scored")]


def main() -> None:
    raise NotImplementedError("Step 5: eval run not built yet")


if __name__ == "__main__":
    main()
