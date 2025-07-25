# Security Agent Commands Help

利用可能なセキュリティ分析コマンドの一覧です。

## Attacker Commands (引数不要)

攻撃者視点の分析コマンド群です。`.claude/commands/attacker/` に格納されています。

- `/attacker/a02_spec` - システム仕様分析
- `/attacker/a03_code` - コード脆弱性検査
- `/attacker/a03b_mutation` - Mutation testing再帰的検査
- `/attacker/a03c_exploit` - RAGベース攻撃シナリオ生成
- `/attacker/a04_scenarios` - 攻撃シナリオ作成
- `/attacker/a05_review` - レッドチーム査定
- `/attacker/a06_poc` - エクスプロイトPoC実装
- `/attacker/a07_report` - セキュリティレポート作成

## Whitehat Commands (引数付き)

防御者視点の分析コマンド群です。`.claude/commands/whitehat/` に格納されています。

### 基本コマンド
- `/whitehat/01_spec <url>` - プロジェクト仕様書生成
  - 例: `/whitehat/01_spec https://reth.rs/overview`

- `/whitehat/01b <folder>` - 監査順序マップ生成
  - 例: `/whitehat/01b utils/` or `/whitehat/01b crates/revm/`

- `/whitehat/02_auditmap <folder> [order_file]` - 監査注釈追加
  - 例: `/whitehat/02_auditmap crates/net/`

- `/whitehat/02b_review <folder> [order_file]` - 監査レビュー
  - 例: `/whitehat/02b_review crates/net/`

### PoC生成コマンド
- `/whitehat/03a_poc_unit <vuln_name> <snippet> <file:line> <output>` - ユニットテストPoC
  - 例: `/whitehat/03a_poc_unit DoSUnboundedImport "fn import_transactions(" crates/net/mod.rs:L100 poc_dos.rs`

- `/whitehat/03b_poc_it <unit_poc> <it_path> <vuln_name>` - 統合テストPoC
  - 例: `/whitehat/03b_poc_it poc_dos.rs tests/it/poc_dos.rs DoSUnboundedImport`

### レポート生成
- `/whitehat/04_report <vuln_name> <snippet> <file> <poc_file> [template] [url]` - Bug Bountyレポート
  - 例: `/whitehat/04_report DoSUnboundedImport "fn import_transactions(" mod.rs poc_dos.rs`

## ワークフロー例

### Attacker フロー
1. `/a02_spec` - 仕様分析
2. `/a03_code` - コード検査
3. `/a04_scenarios` - シナリオ作成
4. `/a05_review` - レビュー
5. `/a06_poc` - PoC作成
6. `/a07_report` - レポート生成

### Whitehat フロー
1. `/01_spec https://example.com` - 仕様書生成
2. `/01b crates/` - 監査順序作成
3. `/02_auditmap crates/` - 監査実施
4. `/02b_review crates/` - レビュー
5. `/03a_poc_unit ...` - PoC作成
6. `/04_report ...` - レポート生成

---

このヘルプを表示するには: `/security`
