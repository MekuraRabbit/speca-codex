# RQ2b: 動的テストとの比較 (ProFuzzBench)

**ベンチマーク:** ChatAFL (NDSS 2024) ProFuzzBench テキストベースプロトコル
**Issue:** https://github.com/NyxFoundation/security-agent/issues/96
**状態:** ドラフト（手直し中、変更の可能性あり）

## 概要

ChatAFL 論文で評価された 6 つのプロトコル実装に対して、
SPECA の仕様チェックとファジングの **相補性** を示す。

**直接比較は不可能** — ChatAFL はクラッシュベース (branch coverage, state transitions)、
SPECA は仕様違反ベース (precision, spec violations)。
→ バグ単位の突合せ比較で相補性を実証する。

## 対象プロトコル (6 subjects)

| Subject | Protocol | LoC | Version | RFC |
|---------|----------|-----|---------|-----|
| Live555 | RTSP | 57K | 31284aa | RFC 2326 |
| ProFTPD | FTP | 242K | 61e621e | RFC 959 |
| PureFTPD | FTP | 29K | 10122d9 | RFC 959 |
| Kamailio | SIP | 939K | a220901 | RFC 3261 |
| Exim | SMTP | 118K | d6a5a05 | RFC 5321 |
| forked-daapd | DAAP | 79K | 2ca10d9 | (proprietary) |

## Zero-Day Bugs (9件)

| ID | Subject | Type | ChatAFL | AFLNet | NSFuzz | SPECA |
|----|---------|------|---------|--------|--------|-------|
| CA-001 | Live555 | heap-use-after-free | ✓ | ✗ | ✗ | TBD |
| CA-002 | Live555 | heap-use-after-free | ✓ | ✗ | ✗ | TBD |
| CA-003 | Live555 | use-after-return | ✓ | ✗ | ✗ | TBD |
| CA-004 | Live555 | use-after-return | ✓ | ✗ | ✗ | TBD |
| CA-005 | Live555 | heap-buffer-overflow | ✓ | ✓ | ✓ | TBD |
| CA-006 | Live555 | memory-leak | ✓ | ✓ | ✓ | TBD |
| CA-007 | Live555 | heap-use-after-free | ✓ | ✗ | ✓ | TBD |
| CA-008 | ProFTPD | heap-buffer-overflow | ✓ | ✗ | ✗ | TBD |
| CA-009 | Kamailio | memory-leak | ✓ | ✓ | ✓ | TBD |

**ChatAFL: 9/9, AFLNet: 3/9, NSFuzz: 4/9, ChatAFL unique: 5/9**

## ファイル構成

```
benchmarks/rq2b/
  published_baselines.yaml   # 論文データ (Tables III-V, VII)
  ground_truth_bugs.yaml     # 9 zero-day bugs (TODO: 著者コンタクトで詳細追加)
  visualize.py               # 可視化スクリプト (6 figures)
  README.md                  # このファイル

benchmarks/results/rq2b/
  figures/                   # 生成グラフ
  speca/                     # SPECA 結果 (後で追加)
```

## 実行方法

```bash
# 可視化 (baselines-only)
uv run python3 benchmarks/rq2b/visualize.py

# SPECA 結果を含む場合
uv run python3 benchmarks/rq2b/visualize.py --speca-results benchmarks/results/rq2b/speca/speca_rq2b.json
```

## SPECA 照合手順 (SPECA 実行後)

1. 各プロトコル実装に対して SPECA を実行 (RFC 文書を入力)
2. SPECA の出力 (仕様違反リスト) を取得
3. ChatAFL のバグリスト (ground_truth_bugs.yaml) と照合:
   - **パターン A:** ChatAFL バグ → SPECA で検出できたか
   - **パターン B:** SPECA バグ → ChatAFL では未検出か (相補性)
   - **パターン C:** 両者が見つけたバグの重複 → ベン図で可視化

## データソース

### 論文

- **ChatAFL: A Protocol-Aware Fuzzer with Large Language Models**
- 会議: NDSS 2024
- DOI: https://doi.org/10.14722/ndss.2024.24688
- PDF: https://www.ndss-symposium.org/wp-content/uploads/2024-688-paper.pdf
- GitHub (ChatAFL): https://github.com/ChatAFLndss/ChatAFL
- GitHub (ProFuzzBench): https://github.com/profuzzbench/profuzzbench

### ベースライン数値の出典

| データ | 出典 (ChatAFL NDSS 2024 PDF) |
|--------|------------------------------|
| State transitions (24h 平均) | Table III |
| States covered (24h 平均) | Table IV |
| Branch coverage (24h 平均) | Table V |
| Zero-day bugs 9件の詳細 | Table VII |
| ChatAFL vs AFLNet/NSFuzz 改善率 | Section V-C |

> **注意:** Issue #96 では Table V が bugs と記載されていたが、実際は Table VII が zero-day bugs。Table V は branch coverage。

### 対象プロトコルの出典

- 6 subjects は ChatAFL 論文 Section V-A (Table II) の text-based protocols のみ
- Issue #96 では 9 protocols と記載されていたが、binary protocols (DTLS, DNS, SIP-binary) はテキストベースの SPECA と直接比較不可のため除外

### Zero-Day Bugs の出典

| データ | ソース | ステータス |
|--------|--------|-----------|
| Bug ID, subject, type, detected_by | Table VII (NDSS 2024 PDF) | ✅ 転記済 |
| CA-007 function name (`RTPInterface::sendDataOverTCP`) | 論文本文 Section V-D | ✅ 転記済 |
| file, function, line (全9件) | 著者コンタクト待ち | 🔲 未取得 |
| CVE ID | 著者コンタクト待ち | 🔲 未取得 |

### 著者コンタクト先

- Ruijie Meng: ruijie@comp.nus.edu.sg（筆頭著者）
- Marcel Böhme: marcel.boehme@mpi-sp.org（シニア著者）

## TODO

- [ ] ChatAFL 著者にコンタクト (file/function/line 詳細取得)
- [ ] SPECA を 6 プロトコル実装で実行
- [ ] ground_truth_bugs.yaml の speca フィールドを埋める
- [ ] ベン図を生成
