# 結果（Results）

**TL;DR** — On this task the model (gpt-5.4-mini) is near-perfect (initial balanced accuracy 100% on 120 confirmation pairs). Showing it its own first answer for re-audit (two-stage self-review, condition C) did **not** improve accuracy over an independent re-run (condition B): ΔBA = +0.8 pt, 95% CI [0.0, +2.5] (inconclusive, within ±5 pt). Self-review **destroyed** 2–3 correct answers and fixed 0. Matches the pre-registered prediction.

被験モデル: `gpt-5.4-mini-2026-03-17`, `reasoning_effort=low`. 走行: 2026-07-10, 160ペア×A/B/C=480呼び出し, 総コスト ~$0.45. パース失敗 0/480.

## 素の精度（確認セット120）
| 条件 | sensitivity(SAME) | specificity(DIFF) | balanced accuracy |
|---|---|---|---|
| A 初回判定 | 1.000 | 1.000 | **1.000** |
| B 独立再実行 | 0.967 | 0.983 | 0.975 |
| C 二段階セルフレビュー | 0.983 | 0.983 | 0.983 |

## 主要評価項目（事前登録）
**Δ = balanced accuracy_C − balanced accuracy_B = +0.8 pt, 95%CI(層化bootstrap) [+0.0, +2.5] pt**
→ 判定: **この標本では識別不能**（CIが0をまたぐ）**かつ ±5pt以内**。二段階セルフレビューは独立再実行を明確に上回らない。

## 副次
- **正解破壊 A→C**（確認120）: 正→正 118 / 誤→正 **0** / 正→誤 **2** / 誤→誤 0。純改善 −2。難例でも 修正0・破壊1。→ **セルフレビューは 0件を直し、3件を壊した**。
- **誤りの非対称**（確認120）: A=誤統合0/見逃し0、B=1/2、C=1/1。

## 探索（率は母集団へ外挿しない）
- 難例40: A/B とも hard-pos 20/20・hard-neg 19/20、C は hard-pos 19/20。
- 非決定性 A≠B = 3/160。 高確信(≥90)での誤り 0（確認セット）。

## 解釈
現行の推論モデルは日本語⇔ローマ字の同一人物判定に極めて強い（同姓・生年数日差の別人や非自明な読みも、氏名＋クラブ文脈で解く）。モデルが天井に近いと、「もう一度見る」（独立再実行でも自己再監査でも）は直す余地がなく、ノイズ/正解破壊を足すだけになる。文献（外部検証器なしの内在的自己修正は改善しない・劣化しうる）と整合。

## 限界（正直な開示）
- **天井効果**: 初回100%ゆえ「自己修正が誤りを *直す* か」は本タスクでは十分に試せていない（直す誤りがほぼ無く、壊すことしかできなかった）。より難しいタスク/弱いモデルでは動態が変わりうる。
- 小標本（確認120）・正解破壊は生カウント（2件・率化しない）・B/C実行順は固定（時間ドリフト）・被験は単一モデル。

## 再現
`src/analyze.py` が `data/phase1/run_results.json`（生の A/B/C 判定）から本結果を再計算する。`analysis_summary.json` に主要数値。設計・予測は `PREREGISTRATION.md`（走行前コミット）。
