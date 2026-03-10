# SPECA Web アプリケーション設計提案 (未実装)

> 作成日: 2026-02-23
> ステータス: 設計提案のみ。実装は [ann.md #10](ann.md#10-web-アプリ化--可視化出力) で構想中。

---

## 1. 動機

SPECA の出力は JSON + Markdown のみ。以下の課題がある:

- 査読者が PARTIAL JSON を手動で確認する必要がある
- 3 フェーズ監査の推論過程が JSON に埋もれている
- パイプラインのデモが困難（CLI 依存）
- RQ1/RQ2 の結果が静的で動的フィルタリング不可
- Mermaid `.mmd` がレンダリングされていない

学会 Artifact Evaluation での「Available / Functional / Reproduced」バッジ取得を支援する。

---

## 2. アーキテクチャ: Next.js SSG (静的サイト生成)

**選定理由:**

1. GitHub Pages / Vercel で無料ホスティング。査読者がワンクリックでアクセス可能
2. バックエンド不要。既存 JSON 出力を `public/data/` に配置するだけ
3. 既存パイプラインへの影響ゼロ
4. `npm run build` で静的ファイル一式を ZIP 提出可能
5. SSG はプロフェッショナルな外観を提供

---

## 3. ディレクトリ構成

```
security-agent/
├── web/                          # 新規 (既存に影響なし)
│   ├── package.json
│   ├── next.config.js
│   ├── public/data/              # パイプライン出力 JSON コピー先
│   │   ├── rq1/ rq2/ audit/ graphs/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx          # ランディング
│   │   │   ├── rq2/page.tsx      # RQ2 ダッシュボード
│   │   │   ├── rq1/page.tsx      # RQ1 エクスプローラー
│   │   │   ├── audit/page.tsx    # 監査トレイル閲覧
│   │   │   └── graphs/page.tsx   # プログラムグラフ
│   │   ├── components/
│   │   │   ├── charts/           # Recharts / D3
│   │   │   ├── tables/           # TanStack Table
│   │   │   ├── audit-trail/      # 3 フェーズ展開表示
│   │   │   └── code-viewer/      # シンタックスハイライト
│   │   └── lib/
│   │       ├── types.ts          # schemas.py から自動生成
│   │       └── data-loader.ts
│   └── scripts/
│       └── sync-data.sh          # outputs/ -> web/public/data/
├── scripts/orchestrator/         # 変更なし
├── benchmarks/                   # 変更なし
└── outputs/                      # 変更なし
```

---

## 4. 機能一覧

| ページ | 内容 |
|--------|------|
| `/rq2` | ツール比較棒グラフ、CWE カバレッジヒートマップ、統計検定カード、データセット/ツール/CWE フィルタ |
| `/rq1` | クライアント選択タブ、Findings/Matched/Recall サマリー、マッチ/未マッチ Issue テーブル |
| `/audit` | 3 フェーズアコーディオン展開、コードスニペット (Shiki)、Severity/Classification フィルタ |
| `/graphs` | Mermaid.js グラフレンダリング、グラフ要素クリックで関連プロパティにジャンプ |

---

## 5. 技術スタック

### フロントエンド

| カテゴリ | 選定 |
|----------|------|
| フレームワーク | Next.js 14+ (App Router, SSG) |
| 言語 | TypeScript |
| UI | shadcn/ui + Tailwind CSS |
| チャート | Recharts + D3.js |
| テーブル | TanStack Table |
| コードビューア | Shiki |
| グラフ | Mermaid.js |

### ビルド & デプロイ

| カテゴリ | 選定 |
|----------|------|
| ビルド | `next build && next export` |
| ホスティング | Vercel (第一候補) / GitHub Pages |
| CI | GitHub Actions (`sync-data.sh` -> `npm run build` -> デプロイ) |

---

## 6. データフロー

```
outputs/ ──sync-data.sh──> web/public/data/
benchmarks/results/ ──────> web/public/data/
```

- Web アプリはパイプラインの「読み取り専用ビュー」
- 既存コードベースへの変更は一切不要
- 型定義は `pydantic-to-ts` で `schemas.py` から自動生成

---

## 7. 既存コードへの影響: ゼロ

変更が必要なファイル:
- `.gitignore` -- `web/node_modules/`, `web/.next/`, `web/out/` 追加
- `.github/workflows/` -- デプロイ用ワークフロー新規追加のみ

変更不要: `scripts/orchestrator/`, `scripts/run_phase.py`, `prompts/`, `.claude/skills/`, `benchmarks/`, `tests/`, `outputs/`
