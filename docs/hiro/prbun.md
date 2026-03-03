# アーカイブ: 2026-02 バグ修正 PR 記録

> PR: `bug/fix-1`
> タイトル: fix: kijaku.md 記載の全 66 件のバグ修正 (ORC/SCH/CI/BEN 全カテゴリ完了)

---

## 概要

`docs/hiro/kijaku.md` に記載されたバグ 84 件のうち、SEC-C01--C04 (セキュリティ脆弱性 4 件、別 PR 対応済み) と重複 14 件を除く **全 66 件** を修正。4 並列エージェントによる同時修正で全テストパス。

> 個別バグの詳細は [arc/kijaku.md](arc/kijaku.md) を参照。

---

## カテゴリ別サマリー

| カテゴリ | kijaku.md 記載数 | 本 PR 対応 | 別 PR 対応 | 残件 |
|---------|:---------------:|:---------:|:---------:|:----:|
| SEC (セキュリティ) | 4 | 0 | 4 (別 PR 済) | 0 |
| ORC (Orchestrator) | 19 | 19 | 0 | 0 |
| SCH (Schema/Config) | 14 | 13 | 0 | 0* |
| CI (CI/CD) | 18 | 18 | 0 | 0 |
| BEN (Benchmark) | 16 | 16 | 0 | 0 |
| **合計** | **84** | **66** | **4** | **0** |

*SCH: SCH05/SCH06 は重複として 1 件対応。

---

## カテゴリ別修正概要

### ORC -- Orchestrator (19 件)

- `sys.exit()` を `PhaseAbortError` 例外に置換
- resume 正規表現の大文字/小文字問題修正
- Phase04 の property_id 重複排除
- early-exit 時の部分結果保存、`--force` スコープ限定
- `asyncio.Semaphore`/`Lock` 遅延初期化
- watchdog バイナリモード化、最終読み取り追加
- `num_turns` 計算修正 (メッセージ数 -> ターン数)

### SCH -- Schema/Config (13 件)

- `AuditClassification` enum に Phase 03 分類値追加
- `PropertyWithCode` エイリアス + `_sync_fields` validator
- Phase02 merge validator 両リストマージ + 重複排除
- `review_verdict` 型拡張 (`str` -> `ReviewVerdict | str`)
- テストの `sys.modules` 汚染クリーンアップ

### CI -- CI/CD (18 件)

- heredoc 内 JSON 破損修正 (`printf` 方式)
- `actions/upload-artifact` バージョン修正 (`@v6` -> `@v4`)
- `always()` -> `success() || failure()` (キャンセル時対策)
- `master` -> `default_branch` 変数化
- sweagent トークンのログ漏洩防止 (環境変数化)

### BEN -- Benchmark (16 件)

- `ROOT_DIR` パス解決修正 (`parents[1]` -> `parents[2]`)
- `classification_filter=None` 時の戻り値修正
- Semgrep: 言語推定、コード欠損チェック、JSON パースエラー処理
- bootstrap CI 計算の丸め誤差修正 (`int()` -> `round()`)

---

## テスト結果

```
236 passed in 5.10s
```

- 既存 231 テスト全パス + 新規 5 テスト追加 (SCH グループ)
- リグレッションなし
- 4 並列エージェントの修正をパッチマージ後、コンフリクトなし

---

## 変更規模

- **変更ファイル数**: 45 (第 1 回: 12、第 2 回: 33)
- **コミット**: 2 回 (第 1 回 13 件、第 2 回 53 件)

---

> 個別バグの ID、重要度、対象ファイル、修正内容の詳細は [arc/kijaku.md](arc/kijaku.md) を参照。
