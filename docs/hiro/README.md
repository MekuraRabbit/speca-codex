# docs/hiro — SPECA ベンチマーク委託作業ドキュメント

> **最終更新:** 2026-03-04

## ファイル一覧

| ファイル | 種別 | 内容 |
|----------|------|------|
| [issiuse.md](issiuse.md) | 分析 | ベンチマーク定量化の課題一覧・ベースライン考察 |
| [ann.md](ann.md) | 構想 | SPECA 拡張アイデア 14 案 (ブレスト) |
| [RQ2_BENCHMARK_GUIDE.md](RQ2_BENCHMARK_GUIDE.md) | 手順書 | RQ2 ベンチマーク実行ガイド |
| [LOCAL_VERIFICATION_GUIDE.md](LOCAL_VERIFICATION_GUIDE.md) | 手順書 | ローカル環境でのパイプライン検証 |
| [WEB_APP_DESIGN.md](WEB_APP_DESIGN.md) | 設計案 | 結果可視化 Web アプリの設計提案 (未実装) |
| [mobile-setup.md](mobile-setup.md) | セットアップ | スマホから Claude Code SSH 接続ガイド |
| [prbun.md](prbun.md) | アーカイブ | 66 件バグ修正 PR の記録 |
| [arc/kijaku.md](arc/kijaku.md) | バグ管理 | 脆弱性 + ロジックバグ トラッカー (57 件) |
| [引き継ぎ/hikitugi.md](引き継ぎ/hikitugi.md) | 引き継ぎ | プロジェクト状態・引き継ぎドキュメント |

## 作業状況

### 完了済み
- RQ1 Sherlock Ethereum 評価: Recall 100% (15/15), Precision 66.3%
- RQ2 PrimeVul ベースライン: Cppcheck F1=0.633, Flawfinder F1=0.369, Semgrep F1=0.000
- ベースライングラフ 5 枚生成 (`benchmarks/results/rq2/figures/`)
- ベンチマーク課題分析 + 考察 (issiuse.md)
- SPECA 拡張構想 14 案 (ann.md)

### 未完了
- Security Agent の PrimeVul 実行 (RQ2 の中心データ)
- LLM Baseline の修正・再実行
- Bootstrap CI / 統計検定の計算
- Human label (22 件) の手動レビュー
