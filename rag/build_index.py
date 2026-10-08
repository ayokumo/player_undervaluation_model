"""Step 3 (planned): build the pgvector index.

Plan:
* Read player seasons from Postgres, keep rows passing documents.is_indexable.
* Build text and metadata with documents.build_profile.
* Embed with a sentence transformers model (free, runs locally).
* Write to pgvector with metadata (position_group, league, age, minutes) for filtering.
* Also load notes from notes/scouting_notes/ as doc_type "scouting_note", linked by player_id.
"""


def main() -> None:
    raise NotImplementedError("Step 3: index build not built yet")


if __name__ == "__main__":
    main()
