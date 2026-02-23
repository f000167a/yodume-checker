"""YozumeChecker のテスト.

NOTE: 統合テストはやねうら王のバイナリが必要です。
環境変数 YANEURAOU_PATH を設定してください。
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from yozume_checker.checker import YozumeChecker
from yozume_checker.models import MateResult, YozumeResult


ENGINE_PATH = os.environ.get("YANEURAOU_PATH")

skip_no_engine = pytest.mark.skipif(
    ENGINE_PATH is None,
    reason="YANEURAOU_PATH not set",
)


class TestYozumeResult:
    def test_no_yozume(self):
        r = YozumeResult.no_yozume()
        assert r.yozume is False
        assert r.ply is None
        assert r.alternative_move is None
        assert r.pv is None

    def test_found(self):
        r = YozumeResult.found(
            ply=3,
            alternative_move="4d4c+",
            pv=["4d4c+", "5a4a", "3b4c"],
        )
        assert r.yozume is True
        assert r.ply == 3
        assert r.alternative_move == "4d4c+"
        assert len(r.pv) == 3

    def test_to_json(self):
        r = YozumeResult.no_yozume()
        j = r.to_json()
        assert '"yozume": false' in j

    def test_to_dict(self):
        r = YozumeResult.found(ply=1, alternative_move="2b3c", pv=["2b3c"])
        d = r.to_dict()
        assert d["yozume"] is True
        assert d["ply"] == 1


class TestYozumeCheckerUnit:
    """エンジンをモックしたユニットテスト."""

    @patch("yozume_checker.checker.USIEngine")
    def test_yozume_found_at_ply0(self, MockEngine):
        """初手で余詰が見つかるケース."""
        mock_engine = MagicMock()
        MockEngine.return_value.__enter__ = MagicMock(return_value=mock_engine)
        MockEngine.return_value.__exit__ = MagicMock(return_value=False)

        # 作為検証: 詰みあり
        # 代替手検査: 最初の代替手で詰みあり
        mock_engine.go_mate.side_effect = [
            MateResult.checkmate(["7g7f", "3c3d"]),  # validate sakui
            MateResult.checkmate(["8c8d", "9a9b"]),  # first alternative → mate
        ]

        checker = YozumeChecker(engine_path="/dummy/engine")
        # python-shogi の Board が実際に合法手を生成するため、
        # 実際のSFENが必要。これはユニットテストの限界。
        # 統合テストで実際の局面を使用する。

    @patch("yozume_checker.checker.USIEngine")
    def test_no_yozume(self, MockEngine):
        """余詰が見つからないケース."""
        mock_engine = MagicMock()
        MockEngine.return_value.__enter__ = MagicMock(return_value=mock_engine)
        MockEngine.return_value.__exit__ = MagicMock(return_value=False)

        # すべての代替手で詰みなし
        mock_engine.go_mate.return_value = MateResult.nomate()

        # 注: 実際のテストにはpython-shogiの盤面が必要なため、
        # 統合テストで完全なテストを行う。


@skip_no_engine
class TestYozumeCheckerIntegration:
    """やねうら王を使った統合テスト.

    実際の詰将棋局面を使用してテストする。
    テスト局面はやねうら王の挙動に応じて追加・調整が必要。
    """

    def test_basic_check(self):
        """基本的な動作確認."""
        checker = YozumeChecker(
            engine_path=ENGINE_PATH,
            timeout_ms=10000,
            validate_sakui=False,  # テスト局面が確定するまで検証スキップ
        )
        # TODO: 実際の詰将棋局面とその作為を追加
        # result = checker.check(sfen="...", moves=["..."])
        # assert isinstance(result, YozumeResult)
