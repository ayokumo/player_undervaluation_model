"""Structured outputs the language model must fill. These are the only things it may produce besides the final answer."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Route(BaseModel):
    route: Literal["stats", "reports"] = Field(description="stats for records, reports for written notes")


class StatsQuery(BaseModel):
    intent: Literal["rank", "lookup", "compare"] = "rank"
    league: Optional[str] = None
    season: Optional[str] = None
    position_group: Optional[str] = None
    min_age: Optional[int] = None
    max_age: Optional[int] = None
    order_by: Optional[str] = None
    limit: int = 5
    player_names: list[str] = Field(default_factory=list)
    unsupported_metric: bool = False
    missing_item: Optional[str] = None
    unsupported_league: bool = False
