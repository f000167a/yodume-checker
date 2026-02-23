"""やねうら王（USI）エンジンとの通信モジュール."""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

from .models import MateResult

logger = logging.getLogger(__name__)

# デフォルトのgo mateタイムアウト（ミリ秒）
DEFAULT_MATE_TIMEOUT_MS = 30000


class USIEngine:
    """USIプロトコルでやねうら王と通信するクラス.

    Usage:
        engine = USIEngine("/path/to/YaneuraOu")
        engine.start()
        engine.set_position("sfen ...", moves=["7g7f", "3c3d"])
        result = engine.go_mate(timeout_ms=10000)
        engine.quit()
    """

    def __init__(self, engine_path: str | Path) -> None:
        self.engine_path = Path(engine_path)
        self._process: subprocess.Popen | None = None

        if not self.engine_path.exists():
            raise FileNotFoundError(f"Engine not found: {self.engine_path}")

    def start(self) -> None:
        """エンジンプロセスを起動し、USIハンドシェイクを行う."""
        logger.info("Starting engine: %s", self.engine_path)

        self._process = subprocess.Popen(
            [str(self.engine_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        self._send("usi")
        self._wait_for("usiok")

        self._send("isready")
        self._wait_for("readyok")

        logger.info("Engine ready")

    def quit(self) -> None:
        """エンジンを終了する."""
        if self._process and self._process.poll() is None:
            self._send("quit")
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            logger.info("Engine stopped")

    def set_option(self, name: str, value: str) -> None:
        """USIオプションを設定する."""
        self._send(f"setoption name {name} value {value}")

    def set_position(self, sfen: str, moves: list[str] | None = None) -> None:
        """局面をセットする.

        Args:
            sfen: SFEN文字列（"sfen"プレフィックスなし）
            moves: USI形式の手順リスト
        """
        cmd = f"position sfen {sfen}"
        if moves:
            cmd += " moves " + " ".join(moves)
        self._send(cmd)

    def go_mate(self, timeout_ms: int = DEFAULT_MATE_TIMEOUT_MS) -> MateResult:
        """詰み探索を実行する.

        Args:
            timeout_ms: タイムアウト（ミリ秒）

        Returns:
            MateResult: 詰み探索の結果
        """
        self._send(f"go mate {timeout_ms}")
        return self._read_mate_result(timeout_ms)

    def _send(self, command: str) -> None:
        """エンジンにコマンドを送信する."""
        assert self._process is not None, "Engine not started"
        assert self._process.stdin is not None

        logger.debug(">>> %s", command)
        self._process.stdin.write(command + "\n")
        self._process.stdin.flush()

    def _readline(self, timeout_sec: float | None = None) -> str:
        """エンジンから1行読み取る."""
        assert self._process is not None, "Engine not started"
        assert self._process.stdout is not None

        # Note: subprocess.Popen の stdout.readline() はブロッキング。
        # 本格的なタイムアウト制御にはスレッドや select が必要だが、
        # 初期版ではシンプルなブロッキング読み取りを使用。
        line = self._process.stdout.readline().strip()
        if line:
            logger.debug("<<< %s", line)
        return line

    def _wait_for(self, expected: str, timeout_sec: float = 30.0) -> list[str]:
        """指定文字列が来るまで出力を読み取る.

        Returns:
            読み取った全行のリスト
        """
        lines: list[str] = []
        start = time.monotonic()

        while True:
            if time.monotonic() - start > timeout_sec:
                raise TimeoutError(
                    f"Timeout waiting for '{expected}' from engine "
                    f"(waited {timeout_sec}s)"
                )

            line = self._readline()
            if line:
                lines.append(line)
                if line.startswith(expected):
                    return lines

    def _read_mate_result(self, timeout_ms: int) -> MateResult:
        """go mate の結果を読み取る."""
        # go mate のタイムアウトよりやや長く待つ
        timeout_sec = (timeout_ms / 1000) + 10

        try:
            lines = self._wait_for("checkmate", timeout_sec=timeout_sec)
        except TimeoutError:
            logger.warning("Mate search timed out (%dms)", timeout_ms)
            return MateResult.nomate()

        for line in reversed(lines):
            if line.startswith("checkmate "):
                tokens = line.split()
                if len(tokens) >= 2 and tokens[1] == "nomate":
                    return MateResult.nomate()
                elif len(tokens) >= 2 and tokens[1] == "timeout":
                    return MateResult.nomate()
                else:
                    moves = tokens[1:]
                    return MateResult.checkmate(moves)

        return MateResult.nomate()

    def __enter__(self) -> USIEngine:
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.quit()
