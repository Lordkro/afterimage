from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pack:
    id: str
    name: str
    cents: int
    micros: int


PACKS = {
    "starter": Pack("starter", "AfterImage starter credits", 500, 5_000_000),
    "builder": Pack("builder", "AfterImage builder credits", 2000, 20_000_000),
}


def get_pack(pack_id: str) -> Pack | None:
    return PACKS.get(pack_id.strip().lower())
