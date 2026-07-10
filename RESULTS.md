# 結果（Results）

**TL;DR** — On this task the model (gpt-5.4-mini) is near-ceiling: initial (A) is 159/160 overall and 120/120 on the 120 confirmation pairs, so **only 1 error was fixable** and self-review kept it unfixed. **Across all 160 pairs, self-review C and independent re-run B tie at 156/160**; initial-correct→wrong reversals number **3 for each**; the B-vs-C discordant pairs are just 2, **symmetric (1,1)** (川辺 favors C, 髙山 favors B). The pre-registered primary (confirmation-set C vs B) shows C=118 vs B=117, but that 1-pair edge is subset-dependent and cancels over the full set. So there is **no observed advantage of self-review over a blind re-run** (with only 2 discordant pairs, equivalence is not established either) — and "does it fix errors?" is essentially untested (1 fixable error). This is the **ceiling / difficulty-calibration base-point** of a series (serialization decided after seeing this result, not designed as a control up front).

被験モデル: `gpt-5.4-mini-2026-03-17`, `reasoning_effort=low`. 走行: 2026-07-10, 160ペア×A/B/C=480呼び出し, 総コスト ~$0.446 (各行丸め). パース失敗 0/480.

## 全160 記述統計（スコープ明示・率は外挿しない）
| 対象 | A | B | C |
|---|---|---|---|
| 確認120 | 120 | 117 | 118 |
| 難例40 | 39 | 39 | 38 |
| **全160** | **159** | **156** | **156** |
- 全160で **B=C=156（完全同点）**。確認セットの「C+1」はサブセット依存（難例では逆にB+1）。
- 全160 B対C discordant = (B正C誤 1, B誤C正 1) → **1対1で対称**・McNemar p=1.0。

## 素の精度（確認セット120のみ・Aの唯一の誤りは難例側で不在）
| 条件 | sensitivity(SAME) | specificity(DIFF) | balanced accuracy |
|---|---|---|---|
| A 初回判定 | 1.000 | 1.000 | **1.000** |
| B 独立再実行 | 0.967 | 0.983 | 0.975 |
| C 二段階セルフレビュー | 0.983 | 0.983 | 0.983 |

## 主要評価項目（事前登録・確認120の C 対 B）
| | C 正解 | C 誤り |
|---|---|---|
| **B 正解** | 117 | 0 |
| **B 誤り** | 1 | 2 |
- 主結果=件数: C only 正解1（川辺駿）/ B only 正解0 / both wrong 2。観測 118 vs 117 の1件差はサブセット依存。
- 補助: Δ=BA_C−BA_B=+0.8pt。事前登録CI（対応ブートストラップ）[+0.0,+2.5] だが discordant=1で下限が0固定に退化→寄りかからない。McNemar p=1.0 は**「検出力が無い」の意**（同等の強い証拠ではない）。TOSTも主張しない。

## 副次 — 破壊は起きたが C 固有でも C が多いわけでもない
| 遷移 | A→B(確認120) | A→C(確認120) | A→B(全160) | A→C(全160) |
|---|---|---|---|---|
| 正→誤(破壊) | 3 | 2 | **3** | **3** |
| 誤→正(修正) | 0 | 0 | 0 | 0 |
- 全160でAが正解だった159件中の破壊率: A→B・A→C とも 3/159=1.9%（Wilson 0.64–5.4）。**全体では同数**。確認の「B3/C2」はサブセット限定で難例では逆転（C1/B0）→「Bが多く壊す」とは言えない。
- 反転は B・C 両方で起きC固有でない。単発・順序固定ゆえ「追加パス自体が原因」とは断定不可。
- C=A 一致 157/160（確認118/120）。動かした3件は全て誤り方向だが、A=159/160の天井では無作為変更3件が全て初回正解から来る確率98.1%（確認は満点で必然）＝**「3件全て改悪」という事実だけでは、Cが選択的に正解を壊した証拠にはならない**。
- C の CHANGE 内訳（確認120）: KEEP116/CHANGE4。実覆し2件=2件とも破壊（酒井 SAME→DIFF、前 DIFF→SAME conf99）。残2件=「CHANGE宣言だが判定不変」＝出力内の不整合（初回にも `action:KEEP|CHANGE` 流用のスキーマ曖昧さの産物か説明不誠実か判別不能）。

## 唯一の可修正誤り＝同名異人（homonym）
- 全160でAが誤ったのは **P154（荒井悠汰 / "Yuta Arai"）の1件のみ**。荒井悠汰のローマ字は "Yuta Arai" で別人の "Yuta Arai" と**完全一致**＝同名異人。読みで切れず外部照合が要る型で、**Aの唯一の失敗がまさにこれ**（読みの易しさとhomonymの難しさが1件で対照）。**CもKEEPで直さず**。

## 誤りの非対称（確認120・生件数＋Wilson95%）
- A: 誤統合0/60・見逃し0/60。 B: 誤統合1/60・見逃し2/60。 C: 誤統合1/60・見逃し1/60。

## コスト（条件別・全160）
| 条件 | 入力token | 出力token(推論含む) | コスト |
|---|---|---|---|
| A | 46,612 | 23,844 | $0.142 |
| B | 46,612 | 23,614 | $0.141 |
| C | 61,148 | 25,884 | $0.162 |
| 計 | 154,372 | 73,342 | **$0.446** |
Cは叩き台(A出力)込でBより約$0.021(約15%)高い。全体同点ゆえ上積みなし。

## 解釈
被験モデルは氏名＋クラブ在籍歴のエンティティマッチングが確認120/120でほぼ天井。**天井では2回目のパス（盲目でも自己監査でも）は直す余地がなく、C は実質 A の据え置き**。二段階レビューは独立再実行と全体同点。文献（外部検証器なしの内在的自己修正）とは**別ジャンルへの外挿として整合**（Huangは主に推論タスク・Kamoiはタスク横断サーベイ）。Self-Refineの再現ではない。

## 限界・逸脱（要点）
- 天井効果（中心）・可修正誤り1件をCは直さず＝「維持」を測り「修正」は未測。
- **記憶汚染は未対処**: 検証用の知名度層別（事前登録）をクリーンなfame proxy欠如で実行できず。原理的不能でなく今回やれなかった。次セットは無名/合成でfame統制。
- 非マッチ79/80は同姓異given name＝読みで解ける（1件のみhomonym）。ベンチ代表性: 60/60固定・人為構成。単発・単一モデル・`reasoning_effort=low`。
- CI: 実装は層化対応ブートストラップ(ペア単位)。**全160の選手/エンティティIDは全て一意・重複0**＝同一選手が複数ペアに登場する反復測定クラスタは無い（姓/表記の残余類似性までは仮定しない）→エンティティ単位でクラスタ化してもペア単位再標本化と一致し事前登録の後者選択肢と実質同等。退化ゆえ主張に非使用。
- 主推論はp値でなく件数。Wilson後追い実装。独立3回目・不一致ルーティングは未実施。探索(KEEP/CHANGE・出力不整合・川辺逸話・コスト)は事前登録外。

## 再現
`src/analyze.py` が `data/phase1/run_results.json` から本結果を再計算。`analysis_summary.json` に主要数値。設計・予測は `PREREGISTRATION.md`（走行前 `d7a3328`）→ 結果 `fd42585`。**本記事はシリーズ第1回（天井の対照点）**。
