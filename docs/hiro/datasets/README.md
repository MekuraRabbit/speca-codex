# Chainlink V2 監査用データセット

> 2026-03 Code4rena Chainlink Payment Abstraction V2 監査で使用したデータセット一覧

## このフォルダ内のデータセット

### chainlink_v2_audit_patterns.csv (103行)
SPECA Pipeline + 手動監査で検出した全パターンのマッチング結果。

| カラム | 説明 |
|--------|------|
| source | 検出元（alloy_evm, c_kzg 等） |
| severity | vulnerability / potential-vulnerability |
| property_id | SPECA property ID |
| code_path | ファイル:関数:行番号 |
| title | finding タイトル |
| description_excerpt | 概要 |
| keyword_matched | マッチしたキーワード |

### past_defi_patterns.csv (132行)
過去の DeFi 監査コンテスト（C4, Sherlock, CodeHawks）から抽出した Dutch Auction / Oracle / CowSwap 関連の HIGH パターン。

| カラム | 説明 |
|--------|------|
| source | プラットフォーム（code4rena, sherlock） |
| contest | コンテスト名 |
| severity | High / Medium |
| title | finding タイトル |
| description_excerpt | 概要（先頭200文字） |
| keyword_matched | マッチしたキーワード（dutch+auction, reentrancy+callback 等） |

## 大容量データセット（パス参照）

以下のファイルはサイズが大きいため、元の場所を参照:

### outputs/similar_audit_findings.csv (388K行, 18MB)
C4 + Sherlock + CodeHawks の全 HIGH/Medium finding から Chainlink V2 に類似するものを抽出。

| カラム | 説明 |
|--------|------|
| source | プラットフォーム |
| contest | コンテスト名 |
| issue_id | Issue 番号 |
| severity | High / Medium |
| title | finding タイトル |
| description | 全文 |

### benchmarks/data/defi_audit_reports/ (元データ)
| ファイル | 行数 | サイズ |
|---------|------|--------|
| code4rena_all_issues.csv | 3.3M行 | 162MB |
| sherlock_all_issues.csv | 406K行 | 21MB |
| codehawks_all_issues.csv | 80K行 | 3.7MB |

## 探索履歴

9ラウンドの探索で使用:
1. Round 1: 14 expanded patterns → CSV keyword search
2. Round 2: 12 attack surfaces → manual code review
3. Round 3: 2,000件 bulk LLM audit → 104 applicable → 17 high confidence → M-15 のみ有効
4. Round 4-7: Deep audit, combination attacks, fresh sessions
5. Round 8: Constructor/compiler/test coverage analysis
6. Round 9: isValidSignature minBidUsdValue 再評価
7. Round 10: HIGH専用 CSV パターンマッチ（EIP-1271, Dutch Auction, Oracle manipulation, Settlement bugs）

詳細: `docs/hiro/chainlink_v2_audit_progress.md`
