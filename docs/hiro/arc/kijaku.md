# SPECA プロジェクト 脆弱性・バグトラッカー

**作成日**: 2026-02-23
**最終更新**: 2026-03-03
**対象**: プロジェクト全体（オーケストレーター、ベンチマーク、CI/CD、スキーマ、テスト）

---

## ステータスサマリー

| カテゴリ | 合計 | FIXED | OPEN | UNKNOWN |
|----------|------|-------|------|---------|
| セキュリティ脆弱性 (SEC) | 17 | 4 | 5 | 8 |
| オーケストレーター (ORC) | 19 | 19 | 0 | 0 |
| ベンチマーク/評価 (BEN) | 16 | 16 | 0 | 0 |
| CI/CD (CI) | 18 | 18 | 0 | 0 |
| スキーマ/テスト (SCH) | 14 | 14 | 0 | 0 |
| **合計** | **84** | **71** | **5** | **8** |

**修正PR**:
- SEC-C01~C04: 別PR (`claude/confident-lewin`, commit `384269ca`)
- BUG-ORC/SCH/CI/BEN 全66件: 一括PR (`bug/fix-1`)

---

## 重要度別サマリー

| 重要度 | 合計 | FIXED | OPEN | UNKNOWN |
|--------|------|-------|------|---------|
| Critical | 4 | 4 | 0 | 0 |
| High | 15 | 10 | 5 | 0 |
| Medium | 25 | 19 | 0 | 6 |
| Low | 40 | 38 | 0 | 2 |

---

# セキュリティ脆弱性 (SEC)

## FIXED

| ID | 重要度 | 概要 | 修正内容 |
|----|--------|------|----------|
| SEC-C01 | Critical | コマンドインジェクション (`run_command`, `shell=True`) | `shlex.quote()` で全パラメータをエスケープ |
| SEC-C02 | Critical | パストラバーサル (LLM出力パス) | `_is_safe_output_path()` ヘルパー追加 |
| SEC-C03 | Critical | スクリプトインジェクション (GitHub Actions `${{ }}`) | `context.payload` 経由に変更 |
| SEC-C04 | Critical | コマンドインジェクション (`resolve_version`) | `shlex.split()` + `shell=False` に変更 |

## OPEN

### SEC-H01: Gitトークン漏洩（8ワークフロー）【High】

**ファイル**: `.github/workflows/*.yml`

#### 概要
8つのGitHub Actionsワークフローで `GITHUB_PERSONAL_ACCESS_TOKEN` がログに露出するリスクがある。

#### 受け入れ条件
* [ ] 全ワークフローで `${{ secrets.* }}` を `mask` 付きで使用
* [ ] `git clone` / `git push` でトークンがコマンドラインに露出しないこと
* [ ] 8ワークフローの一括置換

---

### SEC-H02: TOCTOU レース（MCP設定ファイル）【High】

**ファイル**: `scripts/orchestrator/runner.py`

#### 概要
MCP設定ファイルの読み取りと使用の間にレースコンディションが存在。攻撃者がファイルを差し替え可能。

#### 受け入れ条件
* [ ] アトミック書き込み実装（`tempfile` + `os.rename`）
* [ ] ファイル権限の検証追加

---

### SEC-H03: レースコンディション（PARTIAL読み取り）【High】

**ファイル**: `scripts/orchestrator/resume.py`, `collector.py`

#### 概要
PARTIALファイルの読み書きにレースコンディションが存在。並行バッチ実行時にデータ破損のリスク。

#### 受け入れ条件
* [ ] アトミック書き込み実装（`tempfile` + `os.rename`）
* [ ] ファイルロック or リネーム方式による排他制御

---

### SEC-H04: sweagent 未ピン留め 【High】

**ファイル**: `pyproject.toml`

#### 概要
sweagent パッケージがバージョンピン留めされておらず、サプライチェーン攻撃のリスク。

#### 受け入れ条件
* [ ] `pyproject.toml` で sweagent のバージョンを固定
* [ ] `uv.lock` で再現可能なビルドを確保

---

### SEC-H05: ワークフロー権限の過剰付与 【High】

**ファイル**: `.github/workflows/*.yml`

#### 概要
複数のワークフローで `permissions` が最小権限原則に反して過剰に付与されている。

#### 受け入れ条件
* [ ] 全ワークフローで `permissions` を必要最小限に設定
* [ ] `contents: write` が不要なワークフローから除去

---

## UNKNOWN（詳細未記載）

以下のセキュリティ脆弱性は元レポートのサマリーテーブルに計上されているが、詳細が未記載。

| ID | 重要度 | 状態 |
|----|--------|------|
| SEC-M01 | Medium | UNKNOWN |
| SEC-M02 | Medium | UNKNOWN |
| SEC-M03 | Medium | UNKNOWN |
| SEC-M04 | Medium | UNKNOWN |
| SEC-M05 | Medium | UNKNOWN |
| SEC-M06 | Medium | UNKNOWN |
| SEC-L01 | Low | UNKNOWN |
| SEC-L02 | Low | UNKNOWN |

---

# ロジックバグ — オーケストレーター (全19件 FIXED)

PR `bug/fix-1` で全件修正済み。

| ID | 重要度 | 概要 | 状態 |
|----|--------|------|------|
| BUG-ORC01 | High | `sys.exit()` を `PhaseAbortError` 例外に置換 | FIXED |
| BUG-ORC02 | High | early-exit結果が `save_partial()` されず消失 → 保存処理追加 | FIXED |
| BUG-ORC03 | High | `resume.py` 正規表現の大文字/小文字不一致 → `re.IGNORECASE` 追加 | FIXED |
| BUG-ORC04 | Medium | `--force --target` が全フェーズ出力を削除 → 対象phaseのみに限定 | FIXED |
| BUG-ORC05 | Medium | Phase04 `load_items` の重複排除なし → dictベースに変更 | FIXED |
| BUG-ORC06 | Medium | `_enrich_with_subgraph_context` がPhase 01eでノーオペ → `file_path` フォールバック追加 | FIXED |
| BUG-ORC07 | Medium | asyncioプリミティブがイベントループ外で生成 → 遅延初期化に変更 | FIXED |
| BUG-ORC08 | Low | batch_indexが1始まり(off-by-one) → 0始まりに修正 | FIXED |
| BUG-ORC09 | Low | LogWatcherのファイルオフセット比較 → バイナリモードに変更 | FIXED |
| BUG-ORC10 | Low | プロンプト先頭の空白が二重lstripで削除 → lstrip除去 | FIXED |
| BUG-ORC11 | Low | cleanup dry-runのカウント不正確 → `counted_logs` setで防止 | FIXED |
| BUG-ORC12 | Low | phase_id "02" のデッドコード → 削除 | FIXED |
| BUG-ORC13 | Low | LogWatcherが stop() 後の最終チャンクを見逃す → 最終読み取り追加 | FIXED |
| BUG-ORC14 | Low | `.claude/debug/latest` が並行バッチ間で汚染 → バッチ固有パスに分離 | FIXED |
| BUG-ORC15 | Low | fallback num_turnsがメッセージ数でカウント → ターン数(÷2)に修正 | FIXED |
| BUG-ORC16 | Low | PARTIALタイムスタンプがqueue/logと不一致 → オプショナルtimestamp追加 | FIXED |
| BUG-ORC17 | Low | 例外ハンドラの (0,0) worker_id/batch_index → プレフィックス追加 | FIXED |
| BUG-ORC18 | Low | 到達不能なKeyError例外ハンドラ → 削除 | FIXED |
| BUG-ORC19 | Low | `_build_prompt` の空白含む引数が曖昧 → `_quote()` ヘルパー追加 | FIXED |

---

# ロジックバグ — ベンチマーク/評価 (全16件 FIXED)

PR `bug/fix-1` で全件修正済み。

| ID | 重要度 | 概要 | 状態 |
|----|--------|------|------|
| BUG-BEN01 | High | `collect_branch_outputs.py` の `ROOT_DIR` が `parents[1]` で誤り → `parents[2]` に修正 | FIXED |
| BUG-BEN02 | Medium | `is_selected_audit_item` のフィルタロジック誤り → `return True` に修正 | FIXED |
| BUG-BEN03 | Medium | Cliff's Delta の計算が誤ラベル → `paired_proportion_diff` にリネーム | FIXED |
| BUG-BEN04 | Medium | Semgrepランナーが全ファイルを .c 拡張子で作成 → language推定追加 | FIXED |
| BUG-BEN05 | Medium | `sample.get("func")` が None の場合にクラッシュ → Noneチェック追加 | FIXED |
| BUG-BEN06 | Medium | Semgrepの非JSON出力でクラッシュ → JSONDecodeErrorハンドリング追加 | FIXED |
| BUG-BEN07 | Medium | タイムスタンプ正規表現がファイル名にマッチしない → パターン修正 | FIXED |
| BUG-BEN08 | Medium | CVEfixesデータセットがSemgrepランナーと非互換 → CODE_KEYSフォールバック追加 | FIXED |
| BUG-BEN09 | Low | cache_read/cache_creationトークンが集計から欠落 → 追加 | FIXED |
| BUG-BEN10 | Low | Semgrepローダーがerror_countを常に0返却 → 実際のエラー数に修正 | FIXED |
| BUG-BEN11 | Low | Semgrepローダーがdictペイロードでクラッシュ → リストラップ追加 | FIXED |
| BUG-BEN12 | Low | security_agentパターンがJSONLローダーと不整合 → 不整合パターン削除 | FIXED |
| BUG-BEN13 | Low | Bootstrap CIが `int()` 切り捨てでバイアス → `round()` に修正 | FIXED |
| BUG-BEN14 | Low | `vul_type` の非0/1整数値でサイレントフォールスルー → 警告分岐追加 | FIXED |
| BUG-BEN15 | Low | `keyword_min_overlap` パラメータがStage 2に効かない → パラメータ化 | FIXED |
| BUG-BEN16 | Low | `fetch_vul4j.sh` のインラインPythonでシェル変数が未エスケープ → シングルクォートheredocに修正 | FIXED |

---

# ロジックバグ — CI/CDワークフロー (全18件 FIXED)

PR `bug/fix-1` で全件修正済み。

| ID | 重要度 | 概要 | 状態 |
|----|--------|------|------|
| BUG-CI01 | High | Heredocで BUG_BOUNTY_SCOPE.json が不正JSON生成 → `printf` 方式に修正 | FIXED |
| BUG-CI02 | High | benchmark-rq1-sherlock-eval で git user.name/email 未設定 → 設定追加 | FIXED |
| BUG-CI03 | High | `actions/upload-artifact@v6` は存在しない → `@v4` に修正 | FIXED |
| BUG-CI04 | High | benchmark-rq2-01-setup でブランチが未プッシュ → `git push` 追加 | FIXED |
| BUG-CI05 | Medium | `RESOLUTION_SUCCESS` が env ではなく output 参照ミス → steps.outputs に修正 | FIXED |
| BUG-CI06 | Medium | `continue-on-error` が全ツールランナーの失敗を隠蔽 → サマリーステップ追加 | FIXED |
| BUG-CI07 | Medium | SSL証明書パスがRHEL/CentOS固有 → ハードコード削除 | FIXED |
| BUG-CI08 | Low | `checkout_ref` が常に空文字列 → 意図説明コメント追加 | FIXED |
| BUG-CI09 | Low | `github.event_name == 'workflow_call'` が常にマッチしない → コメント追加 | FIXED |
| BUG-CI10 | Low | `fromJson` のバリデーション欠如 → 型修正 | FIXED |
| BUG-CI11 | Low | 02c-enrich-code に `force_execute` 入力なし → 入力追加 | FIXED |
| BUG-CI12 | Low | master ブランチ名がハードコード → `default_branch` 変数化 | FIXED |
| BUG-CI13 | Low | benchmark-rq2-03-evaluate が結果を未プッシュ → コミット+プッシュ追加 | FIXED |
| BUG-CI14 | Low | `if: always()` で壊れた状態がプッシュされる可能性 → `success() \|\| failure()` に修正 | FIXED |
| BUG-CI15 | Low | `**` glob が globstar 未有効で動作しない → `find` コマンドに置換 | FIXED |
| BUG-CI16 | Low | スクリプト同期元ブランチの不整合リスク → コメント追加 | FIXED |
| BUG-CI17 | Low | PR番号参照の脆弱性 (workflow_call経由) → null/空ガード追加 | FIXED |
| BUG-CI18 | Low | sweagent-resolver でトークンがCLI引数に露出 → 環境変数に変更 | FIXED |

---

# ロジックバグ — スキーマ/テスト (全14件 FIXED)

PR `bug/fix-1` で全件修正済み。

| ID | 重要度 | 概要 | 状態 |
|----|--------|------|------|
| BUG-SCH01 | High | `AuditClassification` Enum と Phase 03 出力値の不一致 → 4分類値を追加 | FIXED |
| BUG-SCH02 | High | `AuditMapItem` スキーマと Phase 03 プロンプト出力の乖離 → エイリアス+validator追加 | FIXED |
| BUG-SCH03 | Medium | Phase 02c `output_fields` が `code_excerpt` を除外 → 追加 | FIXED |
| BUG-SCH04 | Medium | Severity docstring が実際の比較動作と逆 → docstring修正 | FIXED |
| BUG-SCH05 | Medium | テストが存在しないフィールド名 `affected_boundary` を使用 → `trust_boundary_id` に修正 | FIXED |
| BUG-SCH06 | Medium | TrustAssumption テストが `description` を `text` の代わりに使用 → 修正 | FIXED |
| BUG-SCH07 | Medium | cross-phase テストが `code_scope` の消失を検出しない → テスト追加 | FIXED |
| BUG-SCH08 | Low | Phase02Partial のマージバリデータがデータ消失 → 両リストマージ+重複排除に修正 | FIXED |
| BUG-SCH09 | Low | ReviewVerdict enum が未使用 → `ReviewVerdict \| str` に拡張 | FIXED |
| BUG-SCH10 | Low | Early Exit 結果に audit_trail サブフェーズが欠落 → エントリ追加 | FIXED |
| BUG-SCH11 | Low | ResultCollector テストが processed_ids 追跡を検証しない → テスト追加 | FIXED |
| BUG-SCH12 | Low | `sys.modules` モックがテストセッション全体を汚染 → `patch.dict()` で適切にクリーンアップ | FIXED |
| BUG-SCH13 | Low | CWD依存の `sys.path` 操作 → `Path(__file__).resolve()` に変更 | FIXED |
| BUG-SCH14 | Low | Phase02Partial マージバリデータのテストカバレッジ欠如 → 5テストケース追加 | FIXED |

---

## 対応履歴

| 日付 | PR/コミット | 対応件数 | 内容 |
|------|-------------|----------|------|
| 2026-02-23 | `claude/confident-lewin` (`384269ca`) | 4件 | SEC-C01~C04 Critical脆弱性修正 |
| 2026-02-23 | `bug/fix-1` | 66件 | ORC全19件 + SCH全14件 + CI全18件 + BEN全16件 |
| — | 未着手 | 13件 | SEC-H01~H05(OPEN) + SEC-M01~M06, SEC-L01~L02(UNKNOWN) |
