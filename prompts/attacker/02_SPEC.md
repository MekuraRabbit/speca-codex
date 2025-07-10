### 🎯 目的

* **最終成果物**: `outputs/02_SPEC.json`（純 JSON、スキーマ準拡張版）
* **ゴール**: コードレビューやエクスプロイト創出の土台になる “システムの設計図” を構築

  * **データライフサイクル**（生成→変換→保管→破棄）
  * **コントラクト/モジュール間の依存・呼び出しグラフ**
  * **攻撃面優先度が一目で分かる仕様 vs 実装ギャップ**

---

### 1. 情報収集ポリシー

1. **DOCUMENT\_URL** の**全バージョン／全言語タブを列挙**

   * 最新 Stable / English を軸に、旧バージョン差分もメモ
2. **Reference/API セクション**

   * ABI・定数・ガス値・ロール定義を必ず抽出
3. **外部一次資料**

   * White-paper, Audit report, Medium/Blog, PDF を取得し “research\_sources” に追加
4. **設計変更ログ**

   * V1→V2 などのブレークポイント・機能廃止理由を “design\_changes” に格納

---

### 2. 分析フレームワーク（AI 内部思考チェックリスト）

| フェーズ      | 重点質問例                                                   | JSON マッピング                                     |
| --------- | ------------------------------------------------------- | ---------------------------------------------- |
| **構造把握**  | 「資産が動くエントリーポイントはどこか？」<br>「どのコントラクトが外部コールを発火するか？」        | `system_architecture`, `external_dependencies` |
| **フロー分析** | 「ユーザがdeposit→withdrawするまでの関数列は？」<br>「内部でどのストレージ変数が変わる？」 | `user_flows`, `protocol_specifications`        |
| **要件抽出**  | 「MUST, SHOULD, 最大値, 最小値はいくつ？」<br>「タイムロック秒数、fee上限は？」     | `requirements[]`                               |
| **実装突合**  | 「コードでは誰が \_canSomething()?」<br>「require式は仕様の範囲を守っているか？」 | `compliance_matrix[]`                          |
| **経済評価**  | 「攻撃者が赤字になる設計要素は？」<br>「ガス or 手数料コストは利益を上回るか？」            | `economic_constraints`, `attack_cost_analysis` |
| **脅威列挙**  | 「最悪シナリオで何が壊れる？」<br>「どの依存が停止すると資産凍結？」                    | `potential_security_concerns[]`                |

---

### 3. 生成ロジック強化ポイント

* **関数呼び出しグラフ**

  * `ContractA.funcX -> ContractB.funcY (delegatecall)` の形で列挙
* **ストレージ重要変数カタログ**

  * 例: `totalSupply`, `buffer`, `rewardPerTokenStored` に対し “書換箇所一覧” を注記
* **状態遷移図的要約**

  * `Pending` → `Active` → `Exited` のようなライフサイクルを文章で表現
* **手数料・係数を “式” で示す**

  * `instantRedeemFee = amount * feeRate / FEE_DENOMINATOR`
* **リスク分類タグ**

  * 各 `potential_security_concerns` に `["DoS","Infinite Mint","Oracle Manipulation"]` 等タグ付け

---

### 4. 出力ルール（厳守）

1. **JSONのみ**（Markdown禁止・コードブロック禁止）
2. 不明値は `"Unknown"`／`"Not specified"`。推測記載厳禁
3. 参照 URL は **research\_sources** に配列化（重複不可）
4. **compliance\_matrix** は経済条件を必ず併記
5. 仕様 vs 実装の矛盾は `Mismatch`、意図的変更は `Intentional_Change` と明示

---

### 5. サンプル `requirements` 抽出ルール

```
  {
    "id": "FEE_MAX",
    "text": "The protocol MUST cap any fee at 20%.",
    "source_section": "Docs › Fees › Limits",
    "implementation_context": "PirexEth.setFee(): require(_fee <= MAX_FEE)",
    "design_rationale": "Protects users from governance abuse"
  }
```

---

### 6. 自動思考シグナル

* **❓ 未解決チェック**: “source says X but code missing” → add to `potential_security_concerns`
* **⚠ 仕様抜け**: 要件抜粋で “SHOULD” ばかり、MUST が無い＝セキュリティ曖昧 → flag

---

### 7. 禁止事項（リマインド）

* 経済制約無視で Severity 判定
* 旧バージョン仕様を現実装に強制適用
* 推測による UNKNOWN 以外のステータス
* “手数料高いから危険” など論拠不在のリスク評価
