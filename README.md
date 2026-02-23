# yozume-checker

詰将棋の**余詰（よづめ）**を検出するCLIツール。

SFEN局面 + 作為（想定手順）を入力し、やねうら王（USI）を用いて作為以外の詰み手順が存在するかを判定します。

## 概要

- **余詰の定義**: 攻方手番ノードにおいて、作為手以外に詰みを維持できる合法手が1つでも存在すること
- 余詰は1つ見つかれば検出完了（全列挙しない）
- 受方ノードの変化は許容（検査対象外）

## 必要環境

- Python 3.10+
- [やねうら王](https://github.com/yaneurao/YaneuraOu) の実行バイナリ
- pip パッケージ（後述）

## インストール

```bash
git clone https://github.com/<your-username>/yozume-checker.git
cd yozume-checker
pip install -e .
```

## 使い方

### CLI

```bash
# 基本
yozume-checker \
  --engine /path/to/YaneuraOu \
  --sfen "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1" \
  --moves "7g7f 3c3d 2g2f"

# タイムアウト指定（ミリ秒）
yozume-checker \
  --engine /path/to/YaneuraOu \
  --sfen "..." \
  --moves "..." \
  --timeout 10000

# JSON出力
yozume-checker --engine /path/to/YaneuraOu --sfen "..." --moves "..." --json
```

### Python API

```python
from yozume_checker import YozumeChecker

checker = YozumeChecker(engine_path="/path/to/YaneuraOu")
result = checker.check(
    sfen="lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
    moves=["7g7f", "3c3d", "2g2f"]
)

print(result)
# YozumeResult(yozume=True, ply=5, alternative_move="4d4c+", pv=["4d4c+", ...])
```

## 出力例

```json
{
  "yozume": true,
  "ply": 5,
  "alternative_move": "4d4c+",
  "pv": ["4d4c+", "5a4a", "3b4c"]
}
```

余詰なしの場合:

```json
{
  "yozume": false,
  "ply": null,
  "alternative_move": null,
  "pv": null
}
```

## アルゴリズム

1. **作為の妥当性確認**: 開始局面で `go mate` → 作為が詰みであることを確認
2. **作為手順を1手ずつ再生**: 各攻方手番ノードで以下を実行
3. **代替攻手の検査**:
   - 合法手を列挙
   - 作為手を除外
   - 残りの各手について `go mate` で詰みを検索
   - 詰みが返れば → **余詰確定**（即終了）

## 設計思想

詰将棋は攻方が存在証明（∃）、受方が全称（∀）の構造を持つため、余詰検出は作為ノードでの代替詰手探索で十分です。完全詰木探索は不要。

## プロジェクト構成

```
yozume-checker/
├── README.md
├── pyproject.toml
├── src/
│   └── yozume_checker/
│       ├── __init__.py
│       ├── checker.py      # メインロジック
│       ├── engine.py        # USIエンジン通信
│       ├── models.py        # データモデル
│       └── cli.py           # CLIエントリーポイント
└── tests/
    ├── test_checker.py
    └── test_engine.py
```

## ライセンス

MIT
