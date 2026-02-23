"""データモデル定義."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class YozumeResult:
    """余詰検出の結果.

    Attributes:
        yozume: 余詰が存在するか
        ply: 余詰が見つかった手数（0始まりのply index）
        alternative_move: 作為手の代わりに詰む手（USI形式）
        pv: 代替手からの詰み手順（USI形式のリスト）
    """

    yozume: bool
    ply: int | None = None
    alternative_move: str | None = None
    pv: list[str] | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, **kwargs) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, **kwargs)

    @staticmethod
    def no_yozume() -> YozumeResult:
        return YozumeResult(yozume=False)

    @staticmethod
    def found(ply: int, alternative_move: str, pv: list[str]) -> YozumeResult:
        return YozumeResult(
            yozume=True,
            ply=ply,
            alternative_move=alternative_move,
            pv=pv,
        )


@dataclass(frozen=True)
class MateResult:
    """やねうら王 go mate の結果.

    Attributes:
        found: 詰みが見つかったか
        moves: 詰み手順（USI形式）。見つからなければ空リスト
    """

    found: bool
    moves: list[str]

    @staticmethod
    def checkmate(moves: list[str]) -> MateResult:
        return MateResult(found=True, moves=moves)

    @staticmethod
    def nomate() -> MateResult:
        return MateResult(found=False, moves=[])
