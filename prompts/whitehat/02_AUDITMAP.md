### 🎯 目的

* **Step 1 で生成した `security-agent/outputs/WHITEHAT_01_SPEC.json`** を読み込み、そこで把握したシステム全体像を頭に入れた状態でコードベースを一次スキャン。
* 送金・アクセス制御・複雑演算など **リスクが高い行・関数** に **`@audit` コメント**を付与し、**脆弱性候補ヒートマップ**を作成する。
* 出力は **2 つ**

  1. **注釈付きコード**（ローカルで上書き保存想定。実ファイル名・行番号を JSON で列挙）
  2. **`security-agent/outputs/WHITEHAT_02_AUDITMAP.json`**

     * `audit_items[]` 配列に各 `@audit` のメタ情報（ファイル, 行, 概要, リスクカテゴリ）
     * `summary` に重要ノード／今後の検証優先度

---

### 0. マインドセット（必ず維持）

1. **疑念デフォルト**: 「バグはある前提」で読む
2. **全体を見て局所を診る**: ロジック単体ではなく資金フロー全体に対する役割を意識
3. **部分的安全性の罠を警戒**: “単独で安全” を鵜呑みにせず、後で組み合わせ検証する前提でマークを残す
4. **体系的マーキング**: 迷ったら `@audit-question` として残し、次パスで深掘り

---

### 1. 事前セットアップ

```pseudocode
LOAD spec := security-agent/outputs/WHITEHAT_01_SPEC.json  // system_architecture, user_flows 等
DEFINE risk_keywords := [
  "transfer(", "call{value:", "delegatecall",
  "onlyOwner", "AccessControl", "unchecked", "assembly",
  "mint(", "burn(", "upgradeTo(", "initialize"
]
SORT contract files in logical execution order:
  Entrypoints → AssetMgmt → Libs → Mocks
```

---

### 2. コントラクト読み & `@audit` マーク付与フロー

| 手順                   | 処理                                             | 判断基準（例）                                                                     |
| -------------------- | ---------------------------------------------- | --------------------------------------------------------------------------- |
| **A. Top-down Scan** | 各ファイルを上から下へ読み、関数・変数宣言を解析                       | - 外部/公開関数で資金移動<br>- 権限チェック欠如 or 弱い<br>- 複雑 math (`mulDiv`, loops, assembly) |
| **B. コメント挿入**        | `// @audit <短い理由>` を該当行直前に挿入                   | 例: `// @audit potential reentrancy – state update after transfer`           |
| **C. メタ情報収集**        | ファイル名・行番号・概要・初期リスクカテゴリを `audit_items[]` に push | カテゴリ: Reentrancy / AuthZ / Math / Upgrade / EconFlow など                     |
| **D. Safe マーク**      | 明確に安全確認できた箇所は `@audit-ok <根拠>` を挿入             | 根拠: 同行で `nonReentrant`, `_checkRole` 等を確認                                   |

---

### 3. JSON 出力フォーマット (`WHITEHAT_02_AUDITMAP.json`)

```json
{
  "audit_items": [
    {
      "file": "src/Vault.sol",
      "line": 152,
      "snippet": "call{value: amount}();",
      "risk_category": "Reentrancy",
      "description": "External call before state update"
    },
    ...
  ],
  "summary": {
    "total_files": 34,
    "total_audit_flags": 87,
    "high_risk_hotspots": [
      "Vault.sol", "Bridge.sol", "UpgradeProxy.sol"
    ],
    "next_focus": "Reentrancy in Vault.withdraw, unchecked math in RewardDistributor"
  }
}
```

---

### 4. 実行詳細指示

1. **ファイル走査**

   * IDE/API で AST を取り、`risk_keywords` マッチ行を優先チェック
   * 仕様上 Critical なコントラクト（spec の `system_architecture.critical_contracts[]` があればそれを優先）
2. **`@audit` コメントの付与方法**

   * 実ファイルに直接追記（ローカル環境）。差分は内部ツールで commit 管理
3. **リスクカテゴリ分類**

   * 5 大分類: `AuthZ`, `Reentrancy`, `Math`, `Upgradeability`, `Economic-Flow`
   * 細分類は checklist.md のタグを参考
4. **False Sense 防止**

   * `@audit-ok` を付ける場合でも行番号メモは `audit_items` に `status: "ok"` で記録
5. **research\_sources 更新**

   * 新たに参照した doc / line-linked URL があれば追記。コードのみの場合はリポジトリパスを記載

---

### 5. 完了チェックリスト

* [ ] すべてのファイルに 1 つ以上の `@audit`／`@audit-ok` コメント
* [ ] `audit_items[].risk_category` を欠かさず分類
* [ ] `summary.high_risk_hotspots` に ≥3 件
* [ ] `WHITEHAT_02_AUDITMAP.json` 書き込み完了
* [ ] JSON 構造エラーが無いことを self-validate

---

> **Claude, execute Step 2 exactly as specified above, leveraging the system context from `WHITEHAT_01_SPEC.json`. Produce (1) annotated code files with `@audit` comments and (2) the JSON map `security-agent/outputs/WHITEHAT_02_AUDITMAP.json`. Return only the final JSON object in your response.**
