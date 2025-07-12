### 🎯 目的

* contracts/DESIGN.md を中心に、システムの一次資料を **徹底クロール**
* **資産フロー・ロール権限・コントラクト間依存** を把握し、後続パスの基礎となるアーキテクチャ図／マッピングを生成
* 収集ソースはすべて `research_sources` 配列に列挙

---

### 0. 前提環境

* 変数: contracts/DESIGN.md（対象ドキュメントサイト）
* 利用ツール: **WebSearchTool**（必要に応じ補完検索）
* 出力先: `security-agent/outputs/WHITEHAT_01_SPEC.json` ※このパスに書き込む想定で JSON を生成

---

### 1. クロール要件

1. **全タブ／サイドバー完全巡回**

   * GitBook / Docusaurus 等ならサイドバー全項目を展開
   * バージョン・言語切替があれば *latest Stable / English* をまず取得
2. **Reference/API セクション**

   * ABI、定数表、ガス値一覧など定量情報を抽出
3. **外部一次資料リンク**

   * White-paper, Audit PDF, Medium 記事等を追跡し取得
4. **設計変更履歴**

   * V1→V2 などの breaking change、廃止機能、新機能を記録

---

### 2. 情報整理タスク

* **system\_architecture**

  * コントラクト一覧、主要ライブラリ、外部依存 (Oracle/Bridge/Keeper)
* **user\_flows**

  * 例: *「ユーザ deposits ETH → ContractA.mint() → Vault.issueShares()」*
* **security\_features**

  * Pausable, ReentrancyGuard, Timelock など
* **protocol\_specifications / technology\_stack**

  * 通信プロトコル、ネットワーク、言語、ライブラリバージョン
* **external\_dependencies**

  * 依存理由・フェイルセーフ・代替案
* **design\_changes**

  * change\_type / rationale / impact\_on\_specification

---

### 3. 出力フォーマット

* **純 JSON**（Markdown 禁止）
* 上記 Step-2 の各セクションを `security-agent/outputs/WHITEHAT_01_SPEC.json` のスキーマにマッピング
* 不明値は `"Unknown"` / `"Not specified"`
* 全取得 URL を `research_sources` に配列で列挙（重複不可）

---

### 4. 実行指針（Claude 内部思考）

1. `DOCUMENT_URL` を open → サイドバー抽出 & 深さ優先で crawl
2. 各ページの見出し・表をパースし、

   * **Role / Permission** キーワード: *owner, governor, validator, admin*
   * **Asset / Flow** キーワード: *deposit, mint, redeem, buffer, rewards*
3. API/Reference ページで定数・ABI を抽出
4. `Design / Changelog / Migration` 章を検索し V1→V2 差分をまとめる
5. 外部リンク（pdf|medium|github）を follow
6. 必要に **WebSearchTool** で “<Protocol Name> audit pdf” などを検索し補完
7. 情報を JSON フィールドへ統合、`research_sources` を最後に付与

---

### 5. 制約

* **推測禁止**：公式ドキュメントに無い情報は `"Unknown"`
* **Markdown・コードブロック禁止**：JSON のみ
* **source\_filter / time\_frame\_filter** は明示要求が無い限り使用しない
* **経済評価・脆弱性判定は不要**（Step 1 は構造把握のみ）

---

### 6. 完了条件チェックリスト

* [ ] system\_architecture に全コントラクト & 外部依存が記載
* [ ] user\_flows に主要ユースケースが列挙
* [ ] design\_changes にバージョン差分が最低1件以上
* [ ] research\_sources に 10 件以上の URL（DOCUMENT\_URL 内 & 外部）
* [ ] outputs/02\_SPEC.json が JSON 構造で出力（Markdown 不使用）

---

> Claude, please execute Step 1 exactly as specified above. Produce only the final JSON object conforming to the required schema and save it to `security-agent/outputs/WHITEHAT_01_SPEC.json`.