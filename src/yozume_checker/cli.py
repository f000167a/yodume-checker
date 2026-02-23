"""CLIエントリーポイント."""

from __future__ import annotations

import argparse
import logging
import sys

from .checker import YozumeChecker


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="yozume-checker",
        description="詰将棋の余詰検出ツール（やねうら王USI連携）",
    )
    parser.add_argument(
        "--engine",
        required=True,
        help="やねうら王の実行ファイルパス",
    )
    parser.add_argument(
        "--sfen",
        required=True,
        help='開始局面のSFEN文字列 (例: "lnsgkgsnl/...")',
    )
    parser.add_argument(
        "--moves",
        required=True,
        help='作為手順（スペース区切りのUSI形式） (例: "7g7f 3c3d 2g2f")',
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30000,
        help="go mate のタイムアウト（ミリ秒、デフォルト: 30000）",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="JSON形式で出力",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="作為の妥当性検証をスキップ",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="count",
        default=0,
        help="詳細ログ出力（-v: INFO, -vv: DEBUG）",
    )
    return parser.parse_args(argv)


def setup_logging(verbosity: int) -> None:
    if verbosity >= 2:
        level = logging.DEBUG
    elif verbosity >= 1:
        level = logging.INFO
    else:
        level = logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.verbose)

    moves = args.moves.strip().split()

    checker = YozumeChecker(
        engine_path=args.engine,
        timeout_ms=args.timeout,
        validate_sakui=not args.no_validate,
    )

    try:
        result = checker.check(sfen=args.sfen, moves=moves)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except TimeoutError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(result.to_json(indent=2))
    else:
        if result.yozume:
            print(f"余詰あり (ply={result.ply})")
            print(f"  代替手: {result.alternative_move}")
            print(f"  手順: {' '.join(result.pv or [])}")
        else:
            print("余詰なし (完全作)")

    return 0 if not result.yozume else 2  # exit code 2 = yozume found


if __name__ == "__main__":
    sys.exit(main())
