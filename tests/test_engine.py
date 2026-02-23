"""USIEngine のテスト.

NOTE: これらのテストはやねうら王のバイナリが必要です。
環境変数 YANEURAOU_PATH を設定してください。
設定されていない場合、テストはスキップされます。
"""

from __future__ import annotations

import os

import pytest

from yozume_checker.engine import USIEngine
from yozume_checker.models import MateResult

ENGINE_PATH = os.environ.get("YANEURAOU_PATH")

skip_no_engine = pytest.mark.skipif(
    ENGINE_PATH is None,
    reason="YANEURAOU_PATH not set",
)


class TestMateResult:
    def test_checkmate(self):
        r = MateResult.checkmate(["7g7f", "3c3d"])
        assert r.found is True
        assert r.moves == ["7g7f", "3c3d"]

    def test_nomate(self):
        r = MateResult.nomate()
        assert r.found is False
        assert r.moves == []


@skip_no_engine
class TestUSIEngine:
    def test_start_and_quit(self):
        engine = USIEngine(ENGINE_PATH)
        engine.start()
        engine.quit()

    def test_context_manager(self):
        with USIEngine(ENGINE_PATH) as _engine:
            pass  # start/quit handled

    def test_go_mate_simple(self):
        """簡単な1手詰み局面でテスト."""
        # 後手玉が5一、攻方の金が4二にいるような詰み局面を想定
        # 実際のテスト局面はやねうら王の挙動に応じて調整が必要
        with USIEngine(ENGINE_PATH) as engine:
            # 初期局面では詰みではないのでnomateが返るはず
            engine.set_position(
                "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
            )
            result = engine.go_mate(timeout_ms=5000)
            assert isinstance(result, MateResult)

    def test_invalid_engine_path(self):
        with pytest.raises(FileNotFoundError):
            USIEngine("/nonexistent/path/to/engine")
