# RQ2a Human Review Guide

## Summary

| Category | Count | Action |
|----------|-------|--------|
| A: GT一致TP (自動確認) | 31 | AI判定をそのまま採用 |
| B: GT一致FP (自動確認) | 3 | AI判定をそのまま採用 |
| C: GT外 新発見TP候補 | 8 | **要レビュー** |
| D: GT外 FP候補 | 8 | **要レビュー** |
| **合計** | **50** | |

---

## Category A: GT一致TP — 自動確認OK (31行)

これらはGTの既知バグと正確にマッチ。AI reason も正しい。

| Project | Property ID | GT Match | Type |
|---------|-------------|----------|------|
| M1 | PROP-M1-mlk-011 | RA-M1-O1 | Old |
| M1 | PROP-M1-mlk-012 | RA-M1-N1 | New |
| M2b | PROP-M2b-mlk-016 | RA-M2-N6 | New |
| M2b | PROP-M2b-mlk-013 | RA-M2-N3 | New |
| M2b | PROP-M2b-mlk-014 | RA-M2-N4 | New |
| M2b | PROP-M2b-mlk-015 | RA-M2-N5 | New |
| M3 | PROP-M3-mlk-011 | RA-M3-O1 | Old |
| M4 | PROP-M4-mlk-011 | RA-M4-O1 | Old |
| M5 | PROP-M5-mlk-011 | RA-M5-O1 | Old |
| N1 | PROP-N1-npd-011 | RA-N1-O1 | Old |
| N1 | PROP-N1-npd-012 | RA-N1-N1/N3 | New |
| N2 | PROP-N2-npd-017 | RA-N2-N1 | New |
| N2 | PROP-N2-npd-018 | RA-N2-O7 | Old |
| N2 | PROP-N2-npd-012 | RA-N2-O1 | Old |
| N2 | PROP-N2-npd-013 | RA-N2-O2 | Old |
| N2 | PROP-N2-npd-014 | RA-N2-O3/O4 | Old |
| N2 | PROP-N2-npd-015 | RA-N2-O5 | Old |
| N2 | PROP-N2-npd-016 | RA-N2-O6 | Old |
| N3 | PROP-N3-npd-011 | RA-N3-O1 | Old |
| N3 | PROP-N3-npd-012 | RA-N3-N1 | New |
| N4 | PROP-N4-npd-011 | RA-N4-O1 | Old |
| N5 | PROP-N5-npd-017 | RA-N5-N4 | New |
| N5 | PROP-N5-npd-013 | RA-N5-O1 | Old |
| N5 | PROP-N5-npd-014 | RA-N5-N2 | New |
| N5 | PROP-N5-npd-016 | RA-N5-N3 | New |
| U1 | PROP-U1-uaf-011 | RA-U1-O1 | Old |
| U2 | PROP-U2-uaf-003 | RA-U2-O1 | Old |
| U3 | PROP-U3-uaf-011 | RA-U3-O1 | Old |
| U4 | PROP-U4-uaf-008 | RA-U4-O1 | Old |
| U5 | PROP-U5-uaf-001 | RA-U5-O1 | Old |
| U5 | PROP-U5-uaf-011 | RA-U5-N1 | New |

## Category B: GT一致FP — 自動確認OK (3行)

| Project | Property ID | GT Match | AI Reason |
|---------|-------------|----------|-----------|
| N1 | PROP-N1-npd-002 | RA-N1-FP1 | CompressType enum全カバー、再現不可 |
| N1 | PROP-N1-npd-008 | RA-N1-FP2 | 同上 (output stream側) |
| N3 | PROP-N3-npd-001 | RA-N3-FP1 | mapは使用前に必ず初期化 |

---

## Category C: GT外 新発見TP候補 — 要レビュー (8行)

### C1. M1 PROP-M1-mlk-010 — c2ast() List*/Map* leak [AI: TP]
- **場所:** src/c2ast.cpp L34-48
- **主張:** SASS_LIST/MAP分岐でraw pointer確保後、ネスト要素がSASS_ERRORで例外throw → リーク
- **判断ポイント:** 例外パスでSharedPtrに格納前のポインタが本当にリークするか？
- **AI reason:** 最新でも未修正
- **あなたの判定:** TP / FP → ______

### C2. M3 PROP-M3-mlk-004 — nfp_fl_ct_del_offload tunnel ref leak [AI: TP]
- **場所:** drivers/net/.../flower/conntrack.c L851-896
- **主張:** nfp_modify_flow_metadata()失敗時、goto err_free_merge_flowがトンネルIPクリーンアップをスキップ
- **判断ポイント:** エラーパスのgoto先がクリーンアップを本当にスキップするか？
- **AI reason:** 最新でも未修正、GT外の新発見
- **あなたの判定:** TP / FP → ______

### C3. M3 PROP-M3-mlk-006 — nfp_flower_del_offload 同パターン [AI: TP]
- **場所:** drivers/net/.../flower/offload.c L1526-1559
- **主張:** C2と同一パターン（nfp_modify_flow_metadata失敗→トンネル参照リーク）
- **判断ポイント:** C2がTPならこれもTP（同一根本原因の別箇所）
- **あなたの判定:** TP / FP → ______

### C4. M4 PROP-M4-mlk-009 — q6apm_dai_open graph leak [AI: TP]
- **場所:** sound/soc/qcom/qdsp6/q6apm-dai.c L233-309
- **主張:** q6apm_graph_open()成功後のhw_constraint失敗パスがq6apm_graph_close()を呼ばない
- **判断ポイント:** err:ラベルにkfree(prtd)のみでgraph_closeがないのは本当か？
- **AI reason:** 最新でも未修正、GT外の新発見
- **あなたの判定:** TP / FP → ______

### C5. M5 PROP-M5-mlk-001 — damon pid reference leak [AI: TP]
- **場所:** mm/damon/core.c L381-392
- **主張:** damon_free_target()がput_pid(t->pid)を呼ばず、pidリファレンスリーク
- **判断ポイント:** damon_free_targetのコードにput_pidがないか？sysfs beforeterminateコールバックとの関係
- **AI reason:** 最新ではcleanup_targetコールバック追加で修正済み
- **あなたの判定:** TP / FP → ______

### C6. N2 PROP-N2-npd-010 — ReadDOTImage NULL file handle [AI: TP]
- **場所:** coders/dot.c L140-142
- **主張:** OpenBlob()がgzip検出後にfile_info.fileをNULL設定、agread(NULL)でsegfault
- **判断ポイント:** OpenBlobが本当にfileをNULLにしてMagickTrueを返すケースがあるか？
- **AI reason:** 最新でも未修正、GT外の新発見
- **あなたの判定:** TP / FP → ______

### C7. N4 PROP-N4-npd-010 — freenect_network_init error discard [AI: TP]
- **場所:** wrappers/actionscript/server/freenect_network.c L44-67
- **主張:** freenect_network_initSocket()の返り値を破棄、ソケット失敗後もaccept()実行
- **判断ポイント:** これはNPDというよりエラーハンドリング不備。GT定義のNPDに該当するか？
- **AI reason:** 最新でも未修正、GT外の新発見
- **あなたの判定:** TP / FP → ______

### C8. N5 PROP-N5-npd-015 — fetch.c:71 重複報告 [AI: TP]
- **場所:** libraries/libldap/fetch.c L71-80
- **主張:** npd-014と完全に同一の根本原因（ber_strdup NULL未チェック）
- **判断ポイント:** 重複TPとして扱うか？（Issue指示: 同一根本原因でも全てTPとする）
- **あなたの判定:** TP / FP → ______

---

## Category D: GT外 FP候補 — 要レビュー (8行)

### D1. M3 PROP-M3-mlk-003 — devlink params unregister [AI: FP]
- **場所:** drivers/net/.../devlink_param.c L240-250
- **主張:** NSP不可時にdevlink_params_unregisterがスキップされ、param_itemがリーク
- **FP理由:** register時にスキップならunregisterもスキップが正しい。リーク対象なし
- **あなたの判定:** TP / FP → ______

### D2. M4 PROP-M4-mlk-001 — q6asm port buf [AI: FP]
- **場所:** sound/soc/qcom/qdsp6/q6asm.c L548-562
- **主張:** q6asm_audio_client_release()がport->bufを解放しない
- **FP理由:** 呼び出し側が先にunmap→free_bufする設計。kref管理で正しい
- **あなたの判定:** TP / FP → ______

### D3. M4 PROP-M4-mlk-003 — D2の重複 [AI: FP]
- **場所:** 同上
- **FP理由:** mlk-001と同一関数・同一主張
- **あなたの判定:** TP / FP → ______

### D4. M5 PROP-M5-mlk-002 — damon sysfs target leak [AI: FP]
- **場所:** mm/damon/sysfs.c L2177-2199
- **主張:** find_get_pid()がNULL返却時にdamon_new_target()のtが未解放
- **FP理由:** AI曰く「sysfs kobjectリーク」主張が不正確（kobject未作成）
- **注意:** damon_new_target()のtリーク自体は実在する可能性あり。AIのFP理由が妥当か要確認
- **あなたの判定:** TP / FP → ______

### D5. U2 PROP-U2-uaf-004 — peci_device_destroy UAF [AI: FP]
- **場所:** drivers/peci/device.c L205-213
- **主張:** device_unregister後のdevice->deleted書き込みがUAF
- **FP理由:** sysfs/device_for_each_childが追加参照保持、refcountは0にならない
- **あなたの判定:** TP / FP → ______

### D6. U2 PROP-U2-uaf-006 — D5の重複 [AI: FP]
- **場所:** 同上
- **FP理由:** uaf-004と同一主張
- **あなたの判定:** TP / FP → ______

### D7. U3 PROP-U3-uaf-008 — query_free_cb double-free [AI: FP]
- **場所:** src/server.c L1079-1084
- **主張:** resolv_query()でquery_free_cb呼出後にフォールスルー→dangling pointer
- **FP理由:** 記述されたフォールスルーが実際のコードと不一致
- **あなたの判定:** TP / FP → ______

### D8. U5 PROP-U5-uaf-009 — transreg deleteEntry race [AI: FP]
- **場所:** icu4c/source/i18n/transreg.cpp L507-509
- **主張:** deleteEntry()がcompoundFilter解放→aliasがdangling pointer
- **FP理由:** 記述されたシーケンシャルUAFは不正確（実際は別スレッド競合でのみ可能）
- **あなたの判定:** TP / FP → ______

---

## Quick Decision Matrix

C/D項目で迷ったら:

| 判断基準 | → TP | → FP |
|----------|------|------|
| コードパスが実際に到達可能 | TP | - |
| 防御機構が存在する | - | FP |
| proof_traceのコード読みが正確 | TP | - |
| proof_traceのコード読みが不正確 | - | FP |
| エラーパスでのみ発生（OOM等） | TP (severity低め) | - |
| 設計上の意図的動作 | - | FP |
