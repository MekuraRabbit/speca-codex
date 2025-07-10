### 🎯 目的

* **Step 5 のコンポーザビリティ結果**（`security-agent/outputs/WHITEHAT_05_COMPOSE.json`）にリストされた **`combination_issues[]`** と、まだ未評価の **単独 `poc_results[]`**（Step 3）を対象に、

  1. 攻撃者視点での **コスト・利益・ROI** を具体的に算出
  2. 収支が黒字になるか／リスク許容度を超えるかで **“実行可能性 (viable)”** を判定
  3. 結果を **`security-agent/outputs/WHITEHAT_06_ECON.json`** にまとめる。

---

### 0. 必須マインドセット

| 原則               | 意味                                                               |
| ---------------- | ---------------------------------------------------------------- |
| **現実主義**         | “ガス代＋流動性＋価格インパクト＋手数料＋フラッシュローン費用” を全て加味                           |
| **保守的利益推定**      | 最良ケースと平均ケースの両方を見積もり、過大評価を避ける                                     |
| **攻撃者 ROI 視点**   | ROI > 1 かつ 絶対利益 ≥ \$10k を“Viable” とし、それ以下は “Marginal / Unviable” |
| **システム健全性の反証責任** | “コストが利益を上回る” ことを証明できない限り潜在リスクとして扱う                               |

---

### 1. データ入力

```pseudocode
spec         := WHITEHAT_01_SPEC.json
pocResults   := WHITEHAT_03_POC.json
composeRes   := WHITEHAT_05_COMPOSE.json
priceFeeds   := On-chain (Chainlink) or Coingecko API snapshot  // use static price table if offline
gasPrice     := 60 gwei   // configurable default
```

---

### 2. コスト要素定義

| 項目                 | 説明                                                        | デフォルト取得方法                                                        |
| ------------------ | --------------------------------------------------------- | ---------------------------------------------------------------- |
| **gas\_cost**      | `gasUsed * gasPrice * ETH_price`                          | `forge test --gas-report` or Foundry estimate                    |
| **capital\_lock**  | デポジット/流動性提供など一時的に必要な資本                                    | from PoC `required_capital`                                      |
| **flashloan\_fee** | 0.09 % of borrowed amount (Aave v3) unlessプロトコル差あり        | `borrowed * 0.0009`                                              |
| **slippage\_loss** | DEX交換時の価格インパクト                                            | Simulate via UniswapV2 formula or 0.3 % default if not simulated |
| **penalty\_fee**   | protocol-defined penalty / withdrawal fee                 | read from `spec.requirements`                                    |
| **time\_cost**     | if attack spans days (eg validator exit), discount factor | optional                                                         |

---

### 3. 利益要素定義

| 項目                     | 説明                                 |
| ---------------------- | ---------------------------------- |
| **asset\_gain**        | トークン/ETH 取得量 × 現行価格                |
| **price\_manip\_gain** | Oracle manipulationで得る借入 or reward |
| **inflation\_gain**    | 無担保 mint / double withdraw など      |

---

### 4. アルゴリズム

```pseudocode
for issue in composeRes.combination_issues + pocResults.poc_results:
    if issue.status in ["Vuln","Critical","High"]:
        profit = sum(asset_gain_components)
        cost   = gas_cost + flashloan_fee + slippage_loss + penalty_fee
        roi    = (profit - cost) / max(cost, 1)
        viable = (profit - cost >= 10_000) and (roi > 1)
        assign_viability(issue.id, viable, roi, profit, cost)
```

* **ガス計算例**: `gasUsed = 3_100_000`, `gasPrice=60 gwei`, `ETH=$3,500`
  `gas_cost = 3.1M * 60e-9 * 3500 ≈ $651`
* **Liquidity シミュレーション**:

  ```python
  output = x * y / (x + Δx)  # Uniswap constant product;
  slippage = received/ideal -1
  ```

---

### 5. JSON 出力フォーマット (`WHITEHAT_06_ECON.json`)

```json
{
  "economic_evaluations": [
    {
      "id": "Vault.sol:152 ↔ Bridge.finalizeDeposit",
      "adjusted_severity": "Critical",
      "profit_usd": 1250000,
      "cost_breakdown": {
        "gas_usd": 651,
        "flashloan_fee_usd": 18000,
        "slippage_usd": 4500,
        "penalty_usd": 0
      },
      "net_profit_usd": 1224850,
      "roi": 67.1,
      "viability": "Viable",
      "assumptions": [
        "ETH price $3,500",
        "gasPrice 60 gwei",
        "DEX slippage 0.3% on 20k ETH swap"
      ],
      "mitigation_priority": "Immediate circuit-breaker & per-tx cap"
    },
    {
      "id": "RewardDistributor rounding",
      "adjusted_severity": "Medium",
      "profit_usd": 2500,
      "cost_breakdown": {
        "gas_usd": 75,
        "flashloan_fee_usd": 0,
        "slippage_usd": 0,
        "penalty_usd": 0
      },
      "net_profit_usd": 2425,
      "roi": 31.3,
      "viability": "Unviable (profit < $10k)",
      "assumptions": ["gasPrice 60 gwei"],
      "mitigation_priority": "Low"
    }
  ],
  "summary": {
    "issues_analyzed": 18,
    "viable_attacks": 2,
    "total_potential_loss_usd": 1_350_000,
    "largest_single_loss_usd": 1_225_000
  }
}
```

---

### 6. research\_sources 更新

* ユースドチェーンリンク price feed URL、Etherscan tx hash、DEX pool reserves URL などを追記
* checklist.md / past\_attack\_scenarios.jsonl パスは不要（今回は経済評価のみ）

---

### 7. 完了チェックリスト

* [ ] すべての重大 issue に `profit_usd`, `cost_breakdown`, `viability` 計算
* [ ] `summary.viable_attacks` ≥ 0
* [ ] JSON 構造 VALID & saved to `WHITEHAT_06_ECON.json`

---

> **Claude, execute Step 6 exactly as specified above. Use prior outputs for context, perform cost-benefit calculations, and output only the resulting JSON object to `security-agent/outputs/WHITEHAT_06_ECON.json`.**
