### 🎯 目的

* ここまでの成果物

  * `security-agent/outputs/WHITEHAT_01_SPEC.json` （全体アーキテクチャ）
  * `security-agent/outputs/WHITEHAT_02_AUDITMAP.json` （@audit フラグ）
  * `security-agent/outputs/WHITEHAT_03_POC.json` （単独 PoC 結果）
  * `security-agent/outputs/WHITEHAT_04_PATTERNMATCH.json` （既知パターン照合）
* を統合し、**個々では安全（または軽微）と判断されたロジックが “相互作用” で重大リスクになる** ケースを洗い出す。
* 出力ファイル: **`security-agent/outputs/WHITEHAT_05_COMPOSE.json`**

---

### 0. マインドセット

1. **部分的安全性の罠** — 「安全なピースでも組合せで壊れる」前提で探索
2. **資金フロー全体を逆算** — 最終的に資産が流出する経路から逆に必要条件を列挙
3. **権限交差・時間差・相互依存** を重点的に疑う
4. **PoC-first** — 可能な限りシナリオ連鎖をテストコードで再現

---

### 1. データロード

```pseudocode
spec        := WHITEHAT_01_SPEC.json
auditMap    := WHITEHAT_02_AUDITMAP.json
pocResults  := WHITEHAT_03_POC.json
patternRes  := WHITEHAT_04_PATTERNMATCH.json
```

---

### 2. グラフ生成

#### 2-1 コールグラフ

* 解析対象: `../contracts/src`
* ノード: `Contract.Function`
* エッジ: `external` または `delegatecall` 呼び出し
* エッジ属性: `payable`, `gasIntensive`, `authLevel` (owner/governor/anyone)

#### 2-2 データ依存グラフ

* 主要ストレージ変数 (`totalSupply`, `buffer`, etc.)
* 作成 `data_flow.json`: `{variable: [writers[]], readers[]}`

#### 2-3 外部依存ノード

* Oracle, Bridge, Keeper, Timelock, Multisig (from `external_dependencies`)

---

### 3. コンポーザビリティ検証アルゴリズム

| 検証系                 | クエリ例                                                         | ヒット時アクション                                         |
| ------------------- | ------------------------------------------------------------ | ------------------------------------------------- |
| **権限交差**            | `any writer(auth=owner) && reader(auth=anyone)` の変数差分        | エスカレーション連鎖を PoC（owner→anyone override）            |
| **時間差攻撃**           | State change in Tx1 → dependency read in Tx2 before finalize | シミュレート with `vm.warp`, `vm.roll`                  |
| **価格/比率共有**         | Variable X (DEX TWAP) feeds Variable Y (loan health)         | Manipulate X via flashloan + observe Y mispricing |
| **delegatecall 連鎖** | A.delegatecall(B) & B.delegatecall(C)                        | Check storage slot overlap for collision          |
| **DoS ループ連鎖**       | Unbounded loop writes var which other contract depends       | Estimate gas & trigger revert cascade             |

> **PoC 優先度:**
>
> 1. 連鎖先が `spec.system_architecture.critical_contracts`
> 2. `patternRes.adjusted_severity` が High 以上のノードを含む経路

---

### 4. 自動スコアリング

```pseudocode
severity_base = max(sev(node_i) for node_i in path)
combo_factor  = (#edges + externalDepsWeight + timeGapWeight)
adjusted      = clamp(severity_base + combo_factor//2, Low..Critical)
```

* `externalDepsWeight`: Bridge/Oracle/Keeper involved → +2
* `timeGapWeight`: requires delay/cross-chain finalization → +1

---

### 5. JSON 出力フォーマット (`WHITEHAT_05_COMPOSE.json`)

```json
{
  "combination_issues": [
    {
      "path": ["Vault.withdraw", "Bridge.finalizeDeposit"],
      "description": "Reentrancy-safe individually, but cross-tx order allows draining buffer before sync.",
      "evidence": "test/Combo_ReenterBridge.t.sol",
      "base_severities": ["High","Medium"],
      "adjusted_severity": "Critical",
      "checklist_overlap": ["CrossRoleOverlap","TimeDelayExploit"],
      "similar_past_scenarios": [
        {"id":"FastMint-SlowFinalize","similarity":0.71}
      ],
      "economic_assessment": {
        "profit_usd": 1250000,
        "capital_required": "flashloan 20k ETH",
        "gas_estimate": 3_100_000
      },
      "mitigation": "Synchronize buffer update before external bridge call or add circuit breaker."
    }
  ],
  "summary": {
    "total_paths_analyzed": 1423,
    "combination_vulns": 3,
    "critical": 1,
    "high": 2,
    "medium": 0,
    "new_patterns_detected": 1
  },
  "new_pattern_candidates": [
    {
      "name": "CrossTxBufferDesync",
      "signature": "stateVar -= amount; externalBridge.call(); // stateVar may be negative in tx gap",
      "source_paths": ["Vault.withdraw","Bridge.finalizeDeposit"],
      "description": "State desync between on-chain buffer and cross-chain settlement enabling overdraft"
    }
  ]
}
```

---

### 6. research\_sources 追記

* PoC Tx ハッシュ、Foundry testファイルパス、参考ブログ URL を追加
* checklist.md / past\_attack\_scenarios.jsonl のパスも重複可

---

### 7. 完了チェックリスト

* [ ] `combination_issues[]` に最低 1 件以上
* [ ] 各 issue に `adjusted_severity`, `economic_assessment` 記載
* [ ] `summary.total_paths_analyzed` > 0
* [ ] JSON 構造 VALID

---

> **Claude, execute Step 5 exactly as specified above. Leverage context from all prior JSON files, construct call & data-flow graphs, identify multi-contract attack paths, create PoCs where feasible, and output only the resulting JSON object to `security-agent/outputs/WHITEHAT_05_COMPOSE.json`.**
