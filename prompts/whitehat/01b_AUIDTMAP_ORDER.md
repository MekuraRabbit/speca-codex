# ================= WHITEHAT_01b_AUDITMAP_ORDER =================
#
# ■ 目的
#   - `security-agent/outputs/WHITEHAT_01_SPEC.json` の user_flows を起点に、
#     ソースコード `contracts/**/*.sol` を直接解析して
#     **機能ごとに意味のある「チャンク」単位** で関数列を構築する。
#   - 各チャンクには簡潔な「機能メモ」を付与。
#   - 結果を `security-agent/outputs/WHITEHAT_01b_AUDITMAP_ORDER.json`
#     に保存する。
#
# -----------------------------------------------------------------------
# ■ 入力
#   1. security-agent/outputs/WHITEHAT_01_SPEC.json
#        └ user_flows[*] 例:
#           {
#             "action": "User deposits collateral",
#             "contract_function": "Vault.deposit",
#             ...
#           }
#   2. contracts/**/*.sol   ← 解析対象 Solidity ソース一式
#
#
#
# -----------------------------------------------------------------------
# ■ 出力
#   security-agent/outputs/WHITEHAT_01b_AUDITMAP_ORDER.json
#
#   {
#     "function_chunks": [
#       {
#         "chunk_name": "UF-Deposit",           // 任意だが分かりやすく
#         "description": "ユーザが資産を Vault に預け入れる一連の流れ",
#         "functions": [
#           "Vault.deposit",
#           "Vault._preDepositCheck",
#           "Vault._mintShares",
#           "Token.transferFrom",
#           ...
#         ]
#       },
#       {
#         "chunk_name": "UF-Withdraw",
#         "description": "ユーザが資産を引き出す流れ（手数料計算含む）",
#         "functions": [
#           "Vault.withdraw",
#           "Vault._burnShares",
#           "Vault._postWithdrawHook",
#           ...
#         ]
#       }
#     ]
#   }
#
#   - **function_chunks**: チャンクの配列。順序は SPEC.user_flows の並びを保持。
#   - **chunk_name**   : "UF-<action名 or 任意タグ>"
#   - **description**  : 50〜120字で機能を要約（日本語）
#   - **functions**    : 各チャンク内で **深さ優先 (DFS)** した関数リスト
#                        ・"Contract.func" 形式、重複禁止
#                        ・呼び出し元→呼び出し先の順
#
# -----------------------------------------------------------------------
# ■ チャンク生成アルゴリズム
# 0. helper:
#      regex_fn_def   := r'function\s+([A-Za-z0-9_]+)\s*\('
#      regex_callsite := r'([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s*\('
#
# 1. scanSource():
#      - すべての *.sol を読み取り、
#        fileFunctions["Contract.func"] = { "calls":[...], "file":<path> }
#
# 2. function_chunks := []
#
# 3. for UF in SPEC.user_flows (配列順):
#      EP := UF.contract_function            // 例 "Vault.deposit"
#      curChunk := {
#        "chunk_name"  : "UF-" + EP.split(".")[1],   // or action slug
#        "description" : UF.action or "SPEC未記載",
#        "functions"   : []
#      }
#      seen := {}
#      DFS(EP)
#      function_chunks.append(curChunk)
#
#    DFS(fn):
#      if fn in seen: return
#      seen.add(fn)
#      curChunk.functions.append(fn)
#      for callee in fileFunctions[fn].calls:
#          DFS(callee)
#
# 4. JSON = {"function_chunks": function_chunks}
#    インデント 2, UTF-8 で
#    security-agent/outputs/WHITEHAT_01b_AUDITMAP_ORDER.json に保存。
#
# -----------------------------------------------------------------------
# ■ 制約
#   - description 以外に余分なメタ情報は含めない。
#   - コンソール出力（チャット返信）は **生成 JSON オブジェクトのみ**。
#     ログ・説明は不要。
#
# -----------------------------------------------------------------------
# ■ 実行
#   上記ステップを自動で実施し、完了後に
#   security-agent/outputs/WHITEHAT_01b_AUDITMAP_ORDER.json の内容
#   （JSON オブジェクト）だけを返答せよ。
# =======================================================================