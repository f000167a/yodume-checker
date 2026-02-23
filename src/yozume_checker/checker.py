"""余詰検出メインロジック."""

from __future__ import annotations

import logging
from pathlib import Path

import shogi

from .engine import USIEngine, DEFAULT_MATE_TIMEOUT_MS
from .models import YozumeResult

logger = logging.getLogger(__name__)


class YozumeChecker:
    """余詰検出器.

    作為（想定手順）を持つ詰将棋局面に対して、
    作為以外の詰み手順（余詰）が存在するかを検出する。

    Args:
        engine_path: やねうら王の実行ファイルパス
        timeout_ms: go mate のタイムアウト（ミリ秒）
        validate_sakui: 作為の妥当性を事前検証するか
    """

    def __init__(
        self,
        engine_path: str | Path,
        timeout_ms: int = DEFAULT_MATE_TIMEOUT_MS,
        validate_sakui: bool = True,
    ) -> None:
        self.engine_path = Path(engine_path)
        self.timeout_ms = timeout_ms
        self.validate_sakui = validate_sakui

    def check(self, sfen: str, moves: list[str]) -> YozumeResult:
        """余詰検出を実行する.

        Args:
            sfen: 開始局面のSFEN文字列
            moves: 作為手順（USI形式の手リスト）

        Returns:
            YozumeResult: 余詰検出結果

        Raises:
            ValueError: 作為が不正な場合
        """
        logger.info("=== Yozume check start ===")
        logger.info("SFEN: %s", sfen)
        logger.info("Sakui: %s", " ".join(moves))

        with USIEngine(self.engine_path) as engine:
            # Step 1: 作為の妥当性確認
            if self.validate_sakui:
                self._validate_sakui(engine, sfen, moves)

            # Step 2-3: 各攻方ノードで代替手を検査
            return self._search_yozume(engine, sfen, moves)

    def _validate_sakui(
        self, engine: USIEngine, sfen: str, moves: list[str]
    ) -> None:
        """作為が詰みであることを確認する."""
        logger.info("Validating sakui...")
        engine.set_position(sfen)
        result = engine.go_mate(self.timeout_ms)

        if not result.found:
            raise ValueError(
                "作為の検証に失敗: 開始局面から詰みが見つかりません。"
                "局面または作為手順を確認してください。"
            )
        logger.info("Sakui validated: checkmate found")

    def _search_yozume(
        self, engine: USIEngine, sfen: str, moves: list[str]
    ) -> YozumeResult:
        """作為手順の各攻方ノードで代替詰手を探索する.

        重要: USI の go mate は「手番側が相手玉を詰ます」コマンド。
        代替手を指した直後は受方手番なので、そのまま go mate を呼ぶと
        受方→攻方玉の詰み探索になってしまう。

        そのため以下の手順で検査する:
          1. 代替手 m を指す（受方手番になる）
          2. 受方の全合法手 r を列挙
          3. 各 r を指した局面（攻方手番）で go mate
          4. 全ての r で詰みが見つかれば、m で余詰確定

        合法手がない場合（= 代替手が即詰み）も余詰として扱う。
        """
        board = shogi.Board(sfen)

        for ply, move_usi in enumerate(moves):
            move = shogi.Move.from_usi(move_usi)

            if move not in board.legal_moves:
                raise ValueError(
                    f"不正な手: ply={ply}, move={move_usi}"
                )

            # 受方手番（ply=1,3,5,...）→ 手を進めるだけ
            if ply % 2 != 0:
                board.push(move)
                continue

            # --- 攻方手番（ply=0,2,4,...）→ 代替手を検査 ---
            logger.info("Checking ply=%d, sakui_move=%s", ply, move_usi)

            alternative_moves = [
                m for m in board.legal_moves if m != move
            ]

            logger.info(
                "  %d alternative moves to check", len(alternative_moves)
            )

            moves_so_far = moves[:ply]  # ここまでの手順

            for alt_move in alternative_moves:
                alt_usi = alt_move.usi()
                logger.debug("  Testing alt: %s", alt_usi)

                result = self._is_alt_move_mate(
                    engine, board, sfen, moves_so_far, alt_move
                )
                if result is not None:
                    logger.info(
                        "  *** YOZUME FOUND at ply=%d: %s", ply, alt_usi
                    )
                    return YozumeResult.found(
                        ply=ply,
                        alternative_move=alt_usi,
                        pv=result,
                    )

            # この攻方ノードでは余詰なし → 手を進める
            board.push(move)

        logger.info("No yozume found")
        return YozumeResult.no_yozume()

    def _is_alt_move_mate(
        self,
        engine: USIEngine,
        board: shogi.Board,
        sfen: str,
        moves_so_far: list[str],
        alt_move: shogi.Move,
    ) -> list[str] | None:
        """代替手が余詰（全ての受方応手に対して詰み）かを検査する.

        Returns:
            詰み手順（PV）のリスト。余詰でなければ None。
        """
        alt_usi = alt_move.usi()

        # 代替手を指す → 受方手番
        board.push(alt_move)

        try:
            defender_moves = list(board.legal_moves)

            # 受方に合法手がない = 代替手で即詰み
            if not defender_moves:
                logger.debug("    %s → immediate checkmate (no legal moves)", alt_usi)
                return [alt_usi]

            # 受方の全応手について、攻方が詰ませられるか確認
            for def_move in defender_moves:
                def_usi = def_move.usi()
                test_moves = moves_so_far + [alt_usi, def_usi]

                # 受方応手を指した後 = 攻方手番 → go mate が正しく動作
                engine.set_position(sfen, test_moves)
                mate_result = engine.go_mate(self.timeout_ms)

                if not mate_result.found:
                    # この受方応手で逃れがある → 余詰ではない
                    logger.debug(
                        "    %s → %s → nomate (escape found)", alt_usi, def_usi
                    )
                    return None

                logger.debug(
                    "    %s → %s → mate: %s",
                    alt_usi, def_usi, " ".join(mate_result.moves),
                )

            # 全ての受方応手で詰みが見つかった → 余詰
            # PVは最初の受方応手に対する詰み手順を代表として返す
            first_def = defender_moves[0].usi()
            engine.set_position(sfen, moves_so_far + [alt_usi, first_def])
            representative = engine.go_mate(self.timeout_ms)
            pv = [alt_usi, first_def] + representative.moves

            return pv

        finally:
            board.pop()  # 代替手を元に戻す
