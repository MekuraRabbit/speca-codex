### 🎯 目的

* **Step 3 の PoC 結果**（`security-agent/outputs/WHITEHAT_03_POC.json`）を入力とし、検出済み攻撃シナリオを **既知パターン** と照合して重み付けを行う。
* 参照ナレッジ：

  1. **個人チェックリスト** `@security-agent/docs/checklist.md`
  2. **過去の攻撃シナリオ集** `@security-agent/docs/past_attack_scenarios.jsonl`
* 一致度に応じて Severity を調整し、未知のパターンは **新規ライブラリ候補** として登録。
* アップデート結果を **`security-agent/outputs/WHITEHAT_04_PATTERNMATCH.json`** に出力。

---

### 0. マインドセット

1. **差分思考** — 「既知 vs 未知」を峻別し、学習機会を最大化
2. **類推強化** — 決定的一致だけでなく 70% 以上の類似でも“要注目”として扱う
3. **継続学習** — 未知パターンはすぐにライブラリへフィードバックし、次回以降の検出精度を上げる

---

### 1. データロード

```pseudocode
LOAD pocResults   := security-agent/outputs/WHITEHAT_03_POC.json
LOAD checklist    := @security-agent/docs/checklist.md       // Markdown to list<string>
LOAD pastScenarios:= @security-agent/docs/past_attack_scenarios.jsonl // JSONL array
```

---

### 2. キーワード & シグネチャ生成

| ソース                           | 生成物                    | 例                                                           |
| ----------------------------- | ---------------------- | ----------------------------------------------------------- |
| checklist.md                  | `checklistKeywords[]`  | `"reentrancy"`, `"unchecked call"`, `"fee-on-transfer"`     |
| past\_attack\_scenarios.jsonl | `scenarioSignatures[]` | `"delegatecall msg.value reuse"`, `"oracle TWAP flashloan"` |
| pocResults.poc\_results       | `pocSignatures[]`      | `"Vault.withdraw external call before state update"`        |

* **POC 署名生成規則**: `risk_category + key_code_tokens`（大文字小文字無視、stop word 除去）

---

### 3. 照合アルゴリズム

#### 3-1 Checklist キーワードマッチ

```pseudocode
for poc in pocResults:
    poc.checklist_match = [kw for kw in checklistKeywords if kw in poc.attack_hypothesis.lower() or kw in poc.risk_category.lower()]
    if poc.checklist_match != []: poc.severity_boost += 1
```

#### 3-2 過去シナリオ類似度

* 文ベクトル (e.g., cosine using miniLM) または Jaccard over token sets
* `similarity ≥ 0.60` → `scenario_hit` とし Severity +1

```pseudocode
sim = similarity(pocSignature, scenarioSignature)
if sim >= 0.60:
    poc.past_scenario_hits.append({id, similarity})
    poc.severity_boost += 1
```

#### 3-3 未知パターン登録

* `checklist_match == []` **and** `past_scenario_hits == []` **and** `status == "Vuln"`
  → `new_pattern_candidate` へ追加

---

### 4. Severity 調整

```pseudocode
severity_scale = ["Low","Medium","High","Critical"]
poc.adjusted_severity = bump(original, poc.severity_boost)
```

* `bump()` = 1 boost → +1 level, capped at Critical

---

### 5. JSON 出力フォーマット (`WHITEHAT_04_PATTERNMATCH.json`)

```json
{
  "pattern_match_results": [
    {
      "id": "Vault.sol:152",
      "original_severity": "High",
      "adjusted_severity": "Critical",
      "checklist_match": ["Reentrancy"],
      "past_scenario_hits": [
        {"id":"DAO-REENT-2016","similarity":0.78}
      ],
      "status": "Vuln",
      "note": "Severity boosted by checklist & historical DAO reentrancy similarity"
    },
    ...
  ],
  "new_pattern_candidates": [
    {
      "name": "BufferUnderflowWithFee",
      "signature": "buffer -= fee; require(buffer >= 0)",
      "source_poc_id": "PirexEth.instantRedeem",
      "description": "Underflow possible when fee > buffer leading to revert or exploit"
    }
  ],
  "summary": {
    "total_poc": 87,
    "matched_checklist": 42,
    "matched_past_scenarios": 15,
    "new_patterns": 3
  }
}
```

---

### 6. research\_sources 追記

* 追加で参照したシナリオ URL などを `research_sources` に追記。
* checklist.md と past\_attack\_scenarios.jsonl のパスは必ず含める。

---

### 7. 完了チェックリスト

* [ ] すべての `status=="Vuln"` エントリに `adjusted_severity` 反映
* [ ] 類似度計算で ≥0.60 は `past_scenario_hits` に追加
* [ ] `new_pattern_candidates` に未知パターンを記録
* [ ] `WHITEHAT_04_PATTERNMATCH.json` を書き込み
* [ ] JSON 構造が有効

---

> **Claude, execute Step 4 exactly as specified above. Use `security-agent/outputs/WHITEHAT_03_POC.json` as input, cross-reference with the checklist and past scenarios, and output only the final JSON object to `security-agent/outputs/WHITEHAT_04_PATTERNMATCH.json`.**
