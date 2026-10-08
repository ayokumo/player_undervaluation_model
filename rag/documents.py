"""Turn one player season row into a text profile document plus retrieval metadata.

Pure functions only (no database, no network), so they are easy to test.
The text is what gets embedded; the metadata is what retrieval filters on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Players below this many league minutes are excluded from the index so tiny
# samples never show up in answers. 900 = ten full matches. Revisit in step 3.
MIN_MINUTES = 900

# Key per 90 stats shown in the profile for each position group.
# Field names must match columns in the Postgres stats table once step 2 lands.
# Only stats that the chosen source actually provides should stay here
# (FBref advanced stats were removed in Jan 2026, see docs/data_sources.md).
POSITION_STATS: dict[str, list[str]] = {
    "winger": ["goals_p90", "assists_p90", "xg_p90", "xa_p90", "prog_carries_p90", "dribbles_won_p90", "key_passes_p90"],
    "striker": ["goals_p90", "assists_p90", "xg_p90", "shots_p90", "shots_on_target_p90"],
    "attacking_mid": ["goals_p90", "assists_p90", "xa_p90", "key_passes_p90", "prog_passes_p90"],
    "central_mid": ["prog_passes_p90", "key_passes_p90", "tackles_p90", "interceptions_p90"],
    "defender": ["tackles_p90", "interceptions_p90", "clearances_p90", "aerials_won_p90"],
    "goalkeeper": ["saves_p90", "goals_against_p90", "clean_sheets"],
}


@dataclass
class ProfileDocument:
    doc_id: str
    text: str
    metadata: dict = field(default_factory=dict)


def is_indexable(row: dict, min_minutes: int = MIN_MINUTES) -> bool:
    """True if the player season has enough minutes to be worth indexing."""
    minutes = row.get("minutes")
    return minutes is not None and minutes >= min_minutes


def build_profile(row: dict) -> ProfileDocument:
    """Build the text profile and metadata for one player season.

    Missing stats are written as "n/a" rather than dropped, so the LLM can see
    the gap and say "not enough data" instead of assuming a value.
    """
    required = ["player_id", "name", "season", "position_group", "league", "club", "age", "minutes"]
    missing = [k for k in required if row.get(k) is None]
    if missing:
        raise ValueError(f"row is missing required fields: {missing}")

    position = row["position_group"]
    if position not in POSITION_STATS:
        raise ValueError(f"unknown position_group: {position!r}")

    stat_lines = []
    for stat in POSITION_STATS[position]:
        value = row.get(stat)
        shown = "n/a" if value is None else f"{value:.2f}"
        stat_lines.append(f"  {stat}: {shown}")

    text = "\n".join(
        [
            f"Player: {row['name']} (id {row['player_id']})",
            f"Season: {row['season']}",
            f"Position: {position}",
            f"League: {row['league']}  Club: {row['club']}",
            f"Age: {row['age']}  Minutes: {row['minutes']}",
            "Per 90 stats:",
            *stat_lines,
        ]
    )

    metadata = {
        "player_id": row["player_id"],
        "season": row["season"],
        "position_group": position,
        "league": row["league"],
        "age": row["age"],
        "minutes": row["minutes"],
        "doc_type": "stats_profile",
    }
    return ProfileDocument(doc_id=f"{row['player_id']}_{row['season']}", text=text, metadata=metadata)
