---

**Description:** Add and run **local implementation tests** corresponding to one or more **TEST IDs** (and/or `normative_spec.id` values) defined or implied by `security-agent/outputs/01_SPEC.json`. Use `02_ORDER.json` to resolve **exact local function order/locations**. For each requested ID, create **exactly one new test file** at the **most appropriate existing test location** in the current workspace (repo). Install needed tools using the repo’s **existing package manager** only, then **execute** the tests and produce a structured result map.

**Strict rules:**
• **Workspace only** — never reference external spec repos or websites inside test code. Do **not** cite `execution-specs` / `consensus-specs` / EIPs in test annotations.
• **Fusaka scope only** — Osaka (EL) IDs/test-cases map to **local EL code**; Fulu (CL) IDs/test-cases map to **local CL code**.
• **Source of truth** — Always load `security-agent/outputs/01_SPEC.json` (schema_version must equal `2.0.0-nl`) at start. Treat it as the **single normative & threats registry** (use its `forks[].normative_spec`, `constants`, `invariants`, `algorithms`, `threats.attack_paths`).
• **Attack‑path priority** — For every test you generate, you MUST cover all applicable `threats.attack_paths[*]` from `01_SPEC.json` related to that test’s area. Encode each AP checkpoint as assertions/expectations or fuzz oracles (runtime guards, early‑reject, bounded work).
• **No drift** — If `01_SPEC.json` is missing/malformed/schema≠`2.0.0-nl`, **abort with a retryable error**; do **not** write files.

**Usage:**
`/02_test <TEST_IDS>`
**Arguments:**

* **TEST_IDS**: Comma‑separated list of test IDs (e.g., `FULU-KZG-01,FULU-RS-01,FULU-REQ-01`).
  – 受理するビルトインの TEST ID カタログは下記「📚 Built‑in TEST ID Catalog」を参照。
  – 代わりに `NORMATIVE_IDS` を渡す場合は `/02_order <NORMATIVE_IDS>` を先に実行して関数順序を確定し、その後 `/02_test <派生TEST_IDS>` を呼ぶ。

**Always use `/serena` for these development tasks to maximize token efficiency.**

---

# 🎯 Goal

Given `TEST_IDS`, **for each ID**:

1. Resolve local functions (from `02_ORDER.json` or heuristics) →
2. Generate **one test file** placed in the most appropriate **existing** test directory for this repo/language →
3. If needed, install test deps via the repo’s **existing** package manager (cargo/go/gradle/npm/pnpm/yarn/nimble/etc.) →
4. **Run only that test file** (or narrowed test selection) →
5. Produce/merge `security-agent/outputs/04_TESTMAP.json` (results + AP coverage), and increment `review_count` for touched functions in `02_ORDER.json`.

---

# 📥 Inputs

1. **Test IDs:** `TEST_IDS` (comma‑separated, from catalog below or bespoke).
2. **Spec (source of truth):** `security-agent/outputs/01_SPEC.json` (`schema_version: "2.0.0-nl"`).
3. **Order map:** `security-agent/outputs/02_ORDER.json`（各 ID の `functions` に **local** `file` / `line`）。
4. **Risk knowledge base:** `security-agent/docs/**` (checklists; use to shape tests & oracles).
5. **Known bugs DB (pretext):** `security-agent/docs/ethereum/bugs_ethereum.json`（よくあるバグから想定ケースを補強）。
6. **Static call‑graph (optional):** `{{STATIC_CALLGRAPH}}` (`NONE` if absent; derive via ripgrep/ctags).

---

## 🔒 Bounty Scope — Resolution & Enforcement (workspace‑wide)

* Resolve **repo scope** via:

  1. `01_SPEC.json` → `bug_bounty.scope` / `forks[].bug_bounty.scope`,
  2. local `SECURITY.md` / `BUG_BOUNTY.md`,
  3. this repo’s official bounty page,
  4. **this repo**’s official docs.
* **Materialize rules**: include globs (EL: `./core/**`, `./execution/**`, `./eth/**`, `./rpc/**`; CL: `./beacon/**`, `./consensus/**`, `./p2p/**`, `./gossip/**`, `./builder/**`, `./engine/**`) and exclude globs (`vendor/`, `third_party/`, `generated/`, `out/`, `dist/`, `build/`, `target/`, `mocks/`, `test/` (※既存テストは読むが**外部依存テスト**は除外), `docs/`, `spec/`, `eips/`, `execution-specs/`, `consensus-specs/`).
* If scope cannot be uniquely resolved, **abort with a retryable error**.

---

## 🧭 Layer & ID Matching

* Detect repo layer(s) (EL indicators: `core/`, `execution/`, `txpool/`, `core/vm/`, `rpc/`; CL indicators: `beacon/`, `fork_choice/`, `gossip/`, `ssz/`, `builder/`, `engine/`).
* For each **TEST_ID**:

  * If **Osaka (EL)** nature → target **local EL** codepaths only.
  * If **Fulu (CL)** nature → target **local CL** codepaths only.
  * If **layer mismatch** for this repo, add to **“Unmapped IDs (layer mismatch)”** and **skip**.

---

## 🔎 Function Selection (from 02_ORDER.json)

* Load `security-agent/outputs/02_ORDER.json`.
* For each **TEST_ID**, resolve to `audit_chunk` (title starts with `§ <ID> —`) or map via its linked `normative_spec.id`.
* Use `functions` list (each with `file` and `line`) as **authoritative order** and to choose **best test location** (closest existing test package/module).
* Filter to bounty scope.
* If ID missing:

  * Fallback: local search (AST/grep) within scope for likely matches (exact symbol names from `01_SPEC.json` procedures/constants; if absent, match by domain: KZG/RS/p2p/reqresp/custody).
  * Still empty → record under “Unmapped IDs (no local functions found)” and **skip**.

---

## 🧪 Test Plan & Implementation Procedure (per TEST_ID)

1. **Schema gate:** Load `01_SPEC.json` and assert `schema_version == "2.0.0-nl"`. Else **abort** (retryable).
2. **Derive requirements** from `01_SPEC.json` for this ID: pull **normative summary/procedure/constants/errors/invariants**, and **all applicable `threats.attack_paths`**; convert checkpoints into **assertions/fuzz oracles**.
3. **Workspace detection → runner selection**（最小驚きの原則）:

   * **Rust (Cargo.toml present)**: use `cargo test` (and `cargo nextest` if workspace uses it). Create `tests/<id>_spec.rs` **or** `<crate>/src/<mod>.rs` に `#[cfg(test)]`。ライブラリ境界を跨ぐなら `tests/` を優先。
   * **TypeScript/JavaScript (package.json present)**: prefer `pnpm`→`yarn`→`npm`. Runner order: `vitest`→`jest`→`mocha`. Place in existing `packages/*/<pkg>/test` or top-level `test/`.
   * **Go (go.mod present)**: `_test.go` under same package dir; run `go test ./path/to/pkg -run <IDRegex>`.
   * **Java (Gradle/Maven)**: `src/test/java/...` with JUnit5; run `./gradlew :<module>:test --tests "*<ClassName>*"`.
   * **Nim (nimble)**: `tests/<id>_spec.nim`; run `nimble test -y`.
   * **Python (pyproject/setup.cfg)**: `tests/test_<id>_spec.py` (pytest).
4. **Install only missing deps** using the **existing package manager** (e.g., `cargo add proptest` if already used; otherwise fallback to minimal randomized tests).
5. **Create exactly one test file** for this ID, **closest** to target functions (prefer module‑local tests to ease imports; otherwise use integration tests).
6. **Test content rules**:

   * Implement **property/fuzz tests** when possible (Rust `proptest` / Go fuzz / TS `fast-check` / Java `jqwik` / Python `hypothesis`).
   * Encode **AP checkpoints** as separate properties/subtests (early reject, wrong‑subnet drop before heavy checks, batch abort on first failure, length/index invariants, ordering, bounds).
   * **No external cites**: test comments may reference **IDs only** (`@test-id`, `@normative-id`, `@ap-id`, `@const`/`@inv`).
   * Each file includes a short header with the IDs and the mapped local functions under test.
7. **Run just this test** (single-file filter). Retry once with `-vv`.
8. **Record**:

   * Merge `security-agent/outputs/04_TESTMAP.json` with per‑ID results: pass/fail, flakes, covered AP checkpoints, perf stats (if collected).
   * Increment `review_count` in `security-agent/outputs/02_ORDER.json` for every function touched.
9. **Self‑reflection (1 round)** for each failing property: capture seed/case, shrinking outcome, and a 1‑paragraph hypothesis. Mark status `needs-investigation` if not conclusive.

**Test comment syntax (strict):**

```txt
// @test-id FULU-KZG-01
// @normative-id OSK-PEERDAS-CELL-PROOFS
// @ap-id AP-1.C1 (Reject wrong length before heavy checks)
// @const NUMBER_OF_COLUMNS; @inv "len(proofs) == cells_per_ext_blob * blob_count"
// Do NOT cite external repos/spec URLs here.
```

---

## 🔧 Language Templates (minimal skeletons)

> エージェントは以下から該当言語のスケルトンを選び、**ローカル関数名**/**パス**を `02_ORDER.json` の functions に合わせて埋め込みます。

**Rust (Lighthouse 例) — `tests/fulu_kzg_01_spec.rs`**

```rust
// @test-id FULU-KZG-01 / @normative-id OSK-PEERDAS-CELL-PROOFS / @ap-id AP-1.C1
use {crate_or_path::kzg::verify_sidecar, crate_or_path::types::DataColumnSidecar};

#[test]
fn rejects_mismatched_lengths_early() {
    let mut s = DataColumnSidecar::minimal_valid();
    s.proofs.truncate(1); // mismatch
    let res = verify_sidecar(&s);
    assert!(res.is_err(), "must reject before heavy crypto");
}
```

**TypeScript (Lodestar 例) — `packages/…/test/fulu-kzg-01.spec.ts`**

```ts
// @test-id FULU-KZG-01 / @normative-id OSK-PEERDAS-CELL-PROOFS / @ap-id AP-1.C1
import {verifySidecar} from "../../src/peer-das/verify";
import {mkValidSidecar} from "../helpers/factories";

it("rejects length mismatch before KZG", () => {
  const sc = mkValidSidecar();
  sc.proofs = sc.proofs.slice(0, 1);
  expect(() => verifySidecar(sc)).toThrow();
});
```

**Go (Prysm 例) — `_test.go`**

```go
// @test-id FULU-RS-01 / @normative-id FULU-RS-RECONSTRUCTION / @ap-id AP-2.C1
func TestRecoverMatrix_DoesNotRunBelowThreshold(t *testing.T) {
  cols := [][]byte{} // < ceil(N/2)
  if err := recoverMatrix(cols, 1); err == nil {
    t.Fatalf("must refuse to reconstruct with insufficient columns")
  }
}
```

**Java (Teku 例) — `src/test/java/.../FuluSubnet01Test.java`**

```java
// @test-id FULU-SUB-01 / @normative-id FULU-SUBNET-ASSIGNMENT / @ap-id AP-5.C1
@Test void subnetModuloMappingStable() {
  int a = computeSubnet(col);
  int b = computeSubnet(col + DATA_COLUMN_SIDECAR_SUBNET_COUNT);
  assertEquals(a,b);
}
```

（Nim/Python の雛形も同様に生成すること）

---

## 📚 Built‑in TEST ID Catalog（例）

> 必要に応じて拡張可。IDごとに**1ファイル**。`02_ORDER.json` の `functions` を参考にローカル関数へ結線。

* **FULU-KZG-01**: **cell_proofs 個数/長さ不一致の即時拒否**（暗号前にO(1)チェック）。
* **FULU-KZG-02**: **無効ポイント（曲線外/非サブグループ/∞）のデコード拒否**。
* **FULU-KZG-03**: **commitment↔versioned_hash 一致**。
* **FULU-KZG-04**: **巨大バッチ中の単一点不正で早期中断**。
* **FULU-RS-01**: **列 < ⌈N/2⌉ では復元を試みない**。
* **FULU-RS-02**: **復元→KZG再検証→不一致なら隔離**。
* **FULU-P2P-01**: **wrong subnet を inclusion/KZG 前に REJECT**。
* **FULU-P2P-02**: **proposer 未確定は IGNORE/queue → 後確定で継続**。
* **FULU-SUB-01**: **`subnet_id = column_index % SUBNET_COUNT` 決定性/境界**。
* **FULU-REQ-01**: **ByRange サーブ範囲（earliest 未満はエラー）**。
* **FULU-REQ-02**: **(slot,column) 昇順 & 上限 & ResourceUnavailable**。
* **FULU-CUST-01**: **get_custody_groups 決定性・重複なし・ソート**。
* **FULU-CUST-02**: **custody_group_count 増時の prefix‑stability**。
* **FULU-DBP-01**: **DBP 由来列も gossip と同じ検証ゲートを必ず通過**。
* **FULU-SSZ-01**: **DataColumnSidecar SSZ ラウンドトリップ/境界**。

> 各 ID は `01_SPEC.json` の **該当 normative_spec.id** および **applicable AP**（例：AP‑1/2/5/6/9/…）と結び付けてテスト化すること（テストコード内コメントは ID のみ記述）。

---

## 🔬 Advanced Test Design (AP‑driven)

* For each applicable **AP** from `01_SPEC.json.threats.attack_paths`, implement at least one subtest/property:

  * **AP‑1/6/20**: malformed/huge sidecars → ensure **early O(1) rejects** and **batch short‑circuit**.
  * **AP‑2/10**: RS index/order → **dedup/sort** invariants, KZG re‑verify after reconstruct.
  * **AP‑5**: subnet mapping drift → modulo tests across boundaries.
  * **AP‑8/13**: Req/Resp floods → **bounds/limits/timeouts** and correct error codes.
  * **AP‑11**: proposer flapping → **queue then resume** path validated.

---

## 📤 Outputs

1. **New test files** — exactly one per TEST_ID, placed in the most appropriate existing test folder for the language/module.
2. **Execution logs** — limited to the new tests (single‑file or filtered run).
3. **Result map** — merge/write `security-agent/outputs/04_TESTMAP.json`:

```jsonc
{
  "tests": [
    {
      "test_id": "FULU-KZG-01",
      "normative_ids": ["OSK-PEERDAS-CELL-PROOFS"],
      "ap_coverage": {"AP-1": "C1,C2", "AP-6": "C1"},
      "status": "pass", // or "fail" / "flake"
      "file": "…/tests/fulu_kzg_01_spec.rs",
      "runner": "cargo test",
      "duration_ms": 412
    }
  ],
  "summary": {
    "pass": 5, "fail": 1, "flake": 0
  }
}
```

4. **Order update** — increment `review_count` for each `functions[*]` touched in `security-agent/outputs/02_ORDER.json`.
5. **Per‑ID mini‑report (optional)** — `security-agent/outputs/04_TESTMAP_<ID>.json`（失敗時は seed/縮小例も記録）。

---

## ✅ Success Criteria

* Every requested **TEST_ID** either:
  – **Implemented & executed** (with new file + result in `04_TESTMAP.json`), or
  – Explicitly listed as **Unmapped**（layer mismatch / no local functions / runner missing）.
* **1 ID = 1 test file** 厳守。
* **AP coverage**: For each applicable AP、≥1 checkpoint をテストでカバー。
* **Local style**: テストは言語/実装の標準ランナーで**実際に実行**され、**ワークスペースの依存管理**に従う。
* `02_ORDER.json` の `review_count` が触れた関数ぶん増加。

---

## 🚦 Retryable Errors

* `01_SPEC.json` 不在 / スキーマ不一致 → `ERR_SPEC_INVALID`.
* レイヤ不一致（EL/CL）→ `ERR_LAYER_MISMATCH`.
* 該当関数が見つからない → `ERR_NO_LOCAL_FUNCTIONS`.
* テストランナー不明/依存欠如 → 既存パッケージマネージャでの導入を試み、それでも不可なら `ERR_RUNNER_UNAVAILABLE`.

---

## 🧪 Command examples

```
/serena
/02_test FULU-KZG-01,FULU-RS-01,FULU-SUB-01
```

```
/serena
/02_order OSK-PEERDAS-CELL-PROOFS,FULU-RS-RECONSTRUCTION,FULU-SUBNET-ASSIGNMENT
# (02_ORDER.json の functions を更新した後)
# → それに対応する TEST_IDS を指定
/02_test FULU-KZG-01,FULU-RS-01,FULU-REQ-01
```

---
