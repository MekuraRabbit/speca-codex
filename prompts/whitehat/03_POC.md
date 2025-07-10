### 🎯 目的

* **Step 2 で作成した `security-agent/outputs/WHITEHAT_02_AUDITMAP.json`** の `audit_items[]` をすべて再訪問し、実際にエクスプロイト可能かを **PoC（Proof-of-Concept）** で実証または否定する。
* **Step 1 のシステム図 (`security-agent/outputs/WHITEHAT_01_SPEC.json`)** を参照し、資金フロー／依存関係を意識したテスト設計を行う。
* 検証結果を **`security-agent/outputs/WHITEHAT_03_POC.json`** にまとめ、後続の組み合わせリスク評価に引き継ぐ。

---

### 0. マインドセット（必ず維持）

1. **疑念デフォルト** — 「バグはある前提」で PoC を作る
2. **実証主義** — コード上の懸念は必ずテスト or fork で再現して確定
3. **経済合理性** — 攻撃コスト・利益を必ず計算し、現実的か判定
4. **再確認の勇気** — PoC が失敗しても原因を追究して二重確認

---

### 1. 事前セットアップ

```pseudocode
LOAD spec      := security-agent/outputs/WHITEHAT_01_SPEC.json
LOAD auditMap  := security-agent/outputs/WHITEHAT_02_AUDITMAP.json
SETUP Foundry (forge) or Hardhat mainnet-fork at latest block
IMPORT contracts from ../contracts/src/
```

* **Foundry** 推奨：高速・シンプル (`forge test -vvv`)
* Use `forge create` + `vm.startPrank` for role-based tests
* For cross-chain logic, write separate tests per chain or mock bridge

---

### 2. PoC 実装ループ

| 手順              | 内容                                                                                                            | `WHITEHAT_03_POC.json` フィールド   |
| --------------- | ------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| **① 課題取り出し**    | `audit_item` を 1 件取得                                                                                          | `"id"`                         |
| **② 期待動作を明確化**  | spec の `requirements`, `user_flows` を読み「正常系」を理解                                                               | `"expected_behavior"`          |
| **③ 攻撃仮説立案**    | どう入力すれば不変条件を破れるかを文章で記述                                                                                        | `"attack_hypothesis"`          |
| **④ PoC コード作成** | - 単体テスト in Forge (`test_<Name>()`).<br>- もしくは Hardhat script on fork.<br>保存先: `test/<audit_id>.t.sol` or `.js` | `"poc_path"`                   |
| **⑤ 実行 & 結果取得** | `forge test` or `npx hardhat run` で実行し pass/fail をキャプチャ                                                       | `"result": "success" / "fail"` |
| **⑥ 収益/コスト計算**  | `gasUsed`, `required_capital`, `profit_estimate` を算出                                                          | `"profit_usd"`, `"gas"`        |
| **⑦ 結論付け**      | `Vuln` (exploitable), `FP` (false positive), `NeedsReview`                                                    | `"status"`                     |
| **⑧ 次アクション**    | patch アイデア / 追加テスト方針                                                                                          | `"next_steps"`                 |

---

### 3. 経済評価テンプレ

```pseudocode
ETH_cost      = gasUsed * gasPrice
Capital       = upfront deposit / flash-loan fees
Profit        = tokens_drained * market_price
if Profit - ETH_cost - Capital > 0:
    viable = true
else:
    viable = false
```

* **flash-loan** 想定なら資本 0 & fee 0.09% を加味
* **slippage / price impact** は Uniswapフォークでシミュレーション可能 (`IUniswapV3PoolSimulator`)

---

### 4. JSON 出力例 (`WHITEHAT_03_POC.json`)

```json
{
  "poc_results": [
    {
      "id": "Vault.sol:152",
      "risk_category": "Reentrancy",
      "expected_behavior": "withdraw() should send ETH once per user",
      "attack_hypothesis": "Reenter withdraw via fallback before state update",
      "poc_path": "test/Vault_Reentrancy.t.sol",
      "result": "success",
      "gas": 210000,
      "profit_usd": 125000,
      "required_capital": "flashloan 500 ETH",
      "status": "Vuln",
      "next_steps": "Add ReentrancyGuard or CEI ordering"
    },
    ...
  ],
  "summary": {
    "total_audit_items": 87,
    "tested": 87,
    "vuln_count": 5,
    "false_positive": 68,
    "needs_review": 14,
    "critical_paths": ["Vault.withdraw", "Bridge.finalizeDeposit"],
    "max_single_profit_usd": 1250000
  }
}
```

---

### 5. research\_sources 追記

* 生成した PoC tx hash（Etherscan）、GitHub gist、参考資料 URL を `research_sources` に追加
* 重複 URL は除外

---

### 6. 完了チェックリスト

* [ ] すべての `audit_items` に PoC もしくは `FP` 判定
* [ ] `vuln_count` > 0 の場合、各攻撃に **profit\_usd** 記載
* [ ] `WHITEHAT_03_POC.json` 書き込み完了 & JSON 構造 OK
* [ ] PoC ソースファイルが `test/` ディレクトリに保存されていること

---

> **Claude, execute Step 3 exactly as specified above. Leverage the system context from `WHITEHAT_01_SPEC.json` and the audit map from `WHITEHAT_02_AUDITMAP.json`. Produce only the final JSON object (`WHITEHAT_03_POC.json`) in your response and ensure PoC files are saved under `test/`.**
