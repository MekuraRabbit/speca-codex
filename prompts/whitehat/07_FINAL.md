### 🎯 目的

1. **全ステップの成果物を統合し、包括的最終レポート**を作成

   * 仕様・脆弱性・PoC・経済評価・組み合わせリスクを **1 ファイル** に集約
2. **ナレッジベースのアップデート**

   * 新規パターンをチェックリスト／攻撃シグネチャライブラリへ反映
   * 検出漏れ・誤判定要因をメタ学習フィードバックとして保存

---

### 0. インプットファイル

| ステップ | ファイル                                                   | 主な内容             |
| ---- | ------------------------------------------------------ | ---------------- |
| ①    | `security-agent/outputs/WHITEHAT_01_SPEC.json`         | システム仕様 & アーキテクチャ |
| ②    | `security-agent/outputs/WHITEHAT_02_AUDITMAP.json`     | @audit フラグ一覧     |
| ③    | `security-agent/outputs/WHITEHAT_03_POC.json`          | 単独 PoC 結果        |
| ④    | `security-agent/outputs/WHITEHAT_04_PATTERNMATCH.json` | 既知パターン照合         |
| ⑤    | `security-agent/outputs/WHITEHAT_05_COMPOSE.json`      | コンポーザビリティ脆弱性     |
| ⑥    | `security-agent/outputs/WHITEHAT_06_ECON.json`         | 経済的実行性分析         |

追加リソース

* 個人チェックリスト: `@security-agent/docs/checklist.md`
* 攻撃シグニチャ集: `@security-agent/docs/past_attack_scenarios.jsonl`
* (存在すれば) 既存 `pattern_library.json`

---

### 1. マインドセット

| 原則        | 内容                                      |
| --------- | --------------------------------------- |
| **整合性**   | 数値・ステータスの食い違いを残さない。LOC を追って裏取り。         |
| **優先度付け** | Viable & Critical/High を上位、未再現・Low を末尾。 |
| **継続学習**  | 誤判定や見逃し理由を必ずメタデータに記録し、チェックリストへ反映。       |

---

### 2. タスク

#### 2-A 最終レポート生成

* **統合ファイル名**: `security-agent/outputs/WHITEHAT_07_FINAL.json`
* フィールド構成

```json
{
  "system_overview":        (from 01_SPEC),
  "vulnerability_summary":  {critical, high, medium, low, false_positive},
  "issues": [               // 単独 & 組合せ両方
    {
      "id": "",
      "type": "Single|Combination",
      "description": "",
      "severity": "",
      "economic": {profit_usd, cost_usd, roi, viability},
      "status": "Open|Mitigated|FP",
      "evidence": {poc_path, tx_hash},
      "mitigation": "",
      "path": ["Contract.func", ...]       // if combination
    }
  ],
  "new_patterns_added": [                 // from 04 & 05
    {name, signature, source_id}
  ],
  "learning_feedback": {
    "missed_cases": [
      {"reason": "overlooked math edge", "checklist_update": "add mulDiv rounding rule"}
    ],
    "tooling_gaps": ["need automatic TWAP sim"],
    "time_spent_hours": {"reading":2.5,"coding":6.0,"analysis":3.2}
  },
  "research_sources": [...]               // union of all prior sources + new
}
```

* **統合ロジック**

  1. `issues[]` は

     * **Viable** かつ `adjusted_severity >= Medium` → `status:"Open"`
     * Unviable → `status:"Informational"`
     * False positive → `status:"FP"`
  2. Severity は Step 4/5 の boost 済み値を採用。
  3. 経済欄は Step 6 の計算をマージ。

#### 2-B ライブラリアップデート

* **pattern\_library.json**（存在しなければ新規）

  * Append `new_pattern_candidates` から重複チェック 후追加。
  * フォーマット:

    ```json
    {"name":"","signature":"","first_seen_issue_id":"","references":[]}
    ```
* **checklist.md 追記**

  * `learning_feedback.missed_cases[*].checklist_update` を末尾にマークダウン bullet で自動追加。

---

### 3. research\_sources 更新

* すべてのユニーク URL を統合し重複削除。
* checklist.md / past\_attack\_scenarios.jsonl パスを必ず含む。

---

### 4. 完了チェックリスト

* [ ] `WHITEHAT_07_FINAL.json` 作成・JSON VALID
* [ ] `issues[]` に単独・組合せ全て統合
* [ ] `new_patterns_added` ≥ `new_pattern_candidates` from 04/05
* [ ] `pattern_library.json` 更新 or 新規生成
* [ ] `checklist.md` に追記行を付与
* [ ] research\_sources 配列が存在しユニーク URL > 10

---

> **Claude, execute Step 7 exactly as specified above. Merge all prior outputs, generate the comprehensive final report JSON, update the pattern library and checklist markdown, and return ONLY the JSON object `WHITEHAT_07_FINAL.json` in your response.**
