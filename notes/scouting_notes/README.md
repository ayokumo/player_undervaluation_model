# Scouting notes

The 7 notes here were generated from the repo data by `notes/generate_draft_notes.py` (draft, not eyewitness). Each note starts with front matter (note_id, kind, title, author, written, season, leagues, player_ids), which `rag/build_index.py` reads.

Put my own written scouting notes here, one markdown file per note.
Name each file `<player_id>_<short_title>.md` so build_index.py can link it to the player.
These are indexed as doc_type "scouting_note" next to the stats profiles.
