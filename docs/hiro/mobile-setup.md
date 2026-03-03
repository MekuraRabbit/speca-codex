# スマホから Claude Code を使うセットアップガイド

> 個人メモ (hiro 用)

## 前提
- Mac: hironoMacBook-Air.local (192.168.11.33)
- Claude Code: /opt/homebrew/bin/claude
- プロジェクト: /Users/hiro/Documents/security-agent

---

## Step 1: Mac で SSH (リモートログイン) を有効化

**手動でやる必要があります (GUI操作):**

```
システム設定 → 一般 → 共有 → リモートログイン → ON
```

macOS Ventura 以降:
1. 「システム設定」を開く
2. 左メニュー「一般」
3. 「共有」をクリック
4. 「リモートログイン」のトグルを ON にする
5. 「フルディスクアクセスを許可」は OFF のまま
6. ユーザは「すべてのユーザ」か「hiro のみ」を選択

確認:
```bash
ssh localhost echo "OK"
```

---

## Step 2: スマホにターミナルアプリをインストール

### おすすめアプリ

| アプリ | OS | 特徴 | 価格 |
|--------|------|------|------|
| **Termius** | iOS/Android | UI が綺麗、鍵管理が楽 | 無料 (Pro あり) |
| **Blink Shell** | iOS | Mosh 対応、高速 | 有料 |
| **a-Shell** | iOS | ローカルシェル + SSH | 無料 |
| **JuiceSSH** | Android | 軽量 | 無料 |

---

## Step 3: SSH 接続設定

### 同じ Wi-Fi ネットワーク内 (家)

```
Host:     192.168.11.33
Port:     22
User:     hiro
Auth:     パスワード or SSH鍵
```

### 外出先からアクセスしたい場合

選択肢:
1. **Tailscale** (推奨) — VPN なしで P2P 接続。無料
   ```bash
   # Mac に Tailscale をインストール
   brew install --cask tailscale
   # スマホにも Tailscale アプリをインストール
   # 同じアカウントでログイン → Tailscale IP で接続
   ```

2. **ngrok** — 一時的な SSH トンネル
   ```bash
   ngrok tcp 22
   # 表示された tcp://0.tcp.ngrok.io:XXXXX で接続
   ```

3. **ルーターのポートフォワーディング** — 22番ポートを開放 (非推奨、セキュリティリスク)

---

## Step 4: 接続して Claude Code を起動

```bash
# スマホのターミナルから
ssh hiro@192.168.11.33

# プロジェクトディレクトリに移動
cd /Users/hiro/Documents/security-agent

# Claude Code 起動
claude

# または直接ワークツリーで起動
cd /Users/hiro/Documents/security-agent/.claude/worktrees/priceless-jemison
claude
```

### 便利なエイリアス (Mac 側で設定)

~/.zshrc に追加:
```bash
alias speca='cd /Users/hiro/Documents/security-agent && claude'
alias speca-wt='cd /Users/hiro/Documents/security-agent/.claude/worktrees/priceless-jemison && claude'
```

---

## Step 5: セッション維持 (重要)

スマホの画面が消えても SSH セッションが切れないようにする:

### tmux を使う (推奨)
```bash
# Mac 側で tmux がなければインストール
brew install tmux

# SSH 接続後
tmux new -s speca

# Claude Code を起動
cd /Users/hiro/Documents/security-agent
claude

# 画面を閉じたいとき: Ctrl+B → D (デタッチ)
# 再接続: tmux attach -t speca
```

### Mosh を使う (Blink Shell の場合)
```bash
# Mac 側
brew install mosh

# スマホから
mosh hiro@192.168.11.33
```
Mosh は接続が不安定でも自動復帰するので、モバイル向き。

---

## クイックリファレンス

```bash
# SSH 接続
ssh hiro@192.168.11.33

# tmux セッション復帰
tmux attach -t speca || tmux new -s speca

# プロジェクト起動
cd ~/Documents/security-agent && claude

# 現在のワークツリー
cd ~/Documents/security-agent/.claude/worktrees/priceless-jemison && claude

# よく使うコマンド
uv run python3 -m pytest tests/ -v --tb=short    # テスト
uv run python3 scripts/run_phase.py --phase 01a   # Phase 実行
```

---

## トラブルシューティング

### SSH 接続できない
```bash
# Mac 側でリモートログインが ON か確認
sudo systemsetup -getremotelogin
# → Remote Login: On であること

# ファイアウォールが SSH をブロックしていないか確認
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

### claude コマンドが見つからない
```bash
# パスが通っているか確認
which claude
# → /opt/homebrew/bin/claude

# 見つからない場合、SSH 時に .zshrc が読み込まれていない可能性
# ~/.zshrc に以下を追加
export PATH="/opt/homebrew/bin:$PATH"
```

### スマホで日本語入力が文字化けする
```bash
# Mac 側 ~/.zshrc に追加
export LANG=ja_JP.UTF-8
export LC_ALL=ja_JP.UTF-8
```
