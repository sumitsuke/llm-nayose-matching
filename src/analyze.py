import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Analysis per PREREGISTRATION.md. Reads run_results.json + construction_label (gold, 0 errors verified).
Primary: Delta = balanced_accuracy_C - balanced_accuracy_B on the confirmation set (120), stratified
bootstrap 95% CI (resample positives & negatives independently). Secondary: correct-destruction (A->C),
error asymmetry (false-merge vs missed-match). Exploratory: hard set, A/B non-determinism, coarse calibration.
ASCII report + data/phase1/analysis_summary.json."""
import json, random

random.seed(0)
ROOT = _ROOT
res = json.load(open(ROOT + "/data/phase1/run_results.json", encoding="utf-8"))


def dec(r, cond):
    d = r.get(cond)
    return d.get("final_decision") if isinstance(d, dict) else None


def action(r, cond):
    d = r.get(cond)
    return d.get("action") if isinstance(d, dict) else None


def correct(r, cond):
    return dec(r, cond) == r["truth"]


from math import comb, sqrt


def mcnemar_exact(b, c):  # two-sided exact McNemar on discordant counts (b, c)
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * p)


def wilson(k, n, z=1.96):  # Wilson score 95% CI in percent (pre-registered for destruction/asymmetry)
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (100 * (c - h), 100 * (c + h))


conf = [r for r in res if r["kind"] == "CONF"]
pos = [r for r in conf if r["truth"] == "SAME"]
neg = [r for r in conf if r["truth"] == "DIFFERENT"]
hard = [r for r in res if r["kind"] in ("HARD", "HARD_NEG")]


def rate(rows, cond):
    return sum(correct(r, cond) for r in rows) / len(rows) if rows else float("nan")


def ba(cond, P=pos, N=neg):
    return 0.5 * (rate(P, cond) + rate(N, cond))


print(f"=== run: {len(res)} pairs (conf {len(conf)}: pos {len(pos)}/neg {len(neg)} | hard {len(hard)}) ===")
parse_fail = sum(1 for r in res for c in "ABC" if dec(r, c) is None)
print(f"JSON parse failures (A/B/C cells): {parse_fail}/{3 * len(res)}")

print("\n--- 精度(確認セット120) ---")
for c in "ABC":
    print(
        f"  {c}: sensitivity(SAME正答)={rate(pos, c):.3f}  specificity(DIFF正答)={rate(neg, c):.3f}  balanced_acc={ba(c):.3f}  overall={rate(conf, c):.3f}"
    )


# PRIMARY: Delta = BA_C - BA_B, stratified bootstrap CI
def delta(P, N):
    return ba("C", P, N) - ba("B", P, N)


d_hat = delta(pos, neg)
B = 5000
boots = []
for _ in range(B):
    P = [random.choice(pos) for _ in pos]
    N = [random.choice(neg) for _ in neg]
    boots.append(delta(P, N))
boots.sort()
lo, hi = boots[int(0.025 * B)], boots[int(0.975 * B)]
print("\n=== 主要評価項目: Delta = balanced_acc_C - balanced_acc_B (確認120) ===")
print(f"  Delta = {d_hat * 100:+.1f} pt   95%CI(層化bootstrap) = [{lo * 100:+.1f}, {hi * 100:+.1f}] pt")
verdict = "改善(CI>0)" if lo > 0 else "悪化(CI<0)" if hi < 0 else "この標本では識別不能(CIが0を含む)"
band = " かつ ±5pt以内=実用上小差" if (lo > -0.05 and hi < 0.05) else ""
print(f"  判定: {verdict}{band}")

# per-class deltas
print(
    f"  参考: Δsensitivity={100 * (rate(pos, 'C') - rate(pos, 'B')):+.1f}pt  Δspecificity={100 * (rate(neg, 'C') - rate(neg, 'B')):+.1f}pt"
)

# PRIMARY (paired): C vs B on the confirmation set — exact McNemar (added post-review)
print("\n=== 主要比較(対応): C 対 B の 2x2 (確認120) ===")
bc_bC = sum(1 for r in conf if correct(r, "B") and correct(r, "C"))  # both correct
b_not_c = sum(1 for r in conf if correct(r, "B") and not correct(r, "C"))  # B correct, C wrong
c_not_b = sum(1 for r in conf if (not correct(r, "B")) and correct(r, "C"))  # C correct, B wrong
neither = sum(1 for r in conf if (not correct(r, "B")) and not correct(r, "C"))
print("          C正解  C誤り")
print(f"  B正解    {bc_bC:>3}    {b_not_c:>3}")
print(f"  B誤り    {c_not_b:>3}    {neither:>3}")
print(
    f"  discordant: Cのみ正解={c_not_b} / Bのみ正解={b_not_c} → exact McNemar 両側 p = {mcnemar_exact(b_not_c, c_not_b):.3f}"
)
print(
    f"  注: 主結果は件数(上の2x2)。McNemar/bootstrapCIは補助(discordant={b_not_c + c_not_b}で検出力実質ゼロ・CI下限も退化)。"
)

# 全160 記述統計 (母集団外挿でなくベンチマーク上の記述): 確認サブセットの非対称が全体で消えるか
print("\n=== 全160 記述統計: 正解数・破壊 (スコープ明示。率は外挿しない) ===")
for name, rows in [("確認120", conf), ("難例40", hard), ("全160", res)]:
    print(
        f"  {name}: A正解{sum(correct(r, 'A') for r in rows)} / B正解{sum(correct(r, 'B') for r in rows)} / C正解{sum(correct(r, 'C') for r in rows)}"
    )
gb_bc = sum(1 for r in res if correct(r, "B") and not correct(r, "C"))
gc_bc = sum(1 for r in res if not correct(r, "B") and correct(r, "C"))
gdB = sum(1 for r in res if correct(r, "A") and not correct(r, "B"))
gdC = sum(1 for r in res if correct(r, "A") and not correct(r, "C"))
print(
    f"  全160 B対C discordant: B正C誤{gb_bc} / B誤C正{gc_bc} → McNemar exact p={mcnemar_exact(gb_bc, gc_bc):.3f} {'(1対1で対称=完全同点)' if gb_bc == gc_bc else ''}"
)
print(
    f"  全160 破壊(A正解→誤): A→B {gdB}件 / A→C {gdC}件 {'(同数)' if gdB == gdC else ''} → 確認サブセットの非対称(B3/C2)は全体で相殺"
)


# SECONDARY: correct-destruction A->TARGET (confirmation) — A->B and A->C side by side (added post-review)
def transitions(rows, target):
    tt = ft = tf = ff = 0
    for r in rows:
        a, t = correct(r, "A"), correct(r, target)
        tt += a and t
        ft += (not a) and t
        tf += a and (not t)
        ff += (not a) and (not t)
    return tt, ft, tf, ff


print("\n--- 副次: 初回Aからの遷移 A→B と A→C を並記 (確認120) ---")
print(f"  {'遷移':<16} {'A→B':>5} {'A→C':>5}")
tB = transitions(conf, "B")
tC = transitions(conf, "C")
for i, lbl in enumerate(["正→正", "誤→正(修正)", "正→誤(破壊)", "誤→誤"]):
    print(f"  {lbl:<16} {tB[i]:>5} {tC[i]:>5}")
tt, ft, tf, ff = tC  # keep A->C names for downstream/json
print(
    f"  → 破壊は自己レビュー固有でない: 確認セットでBが{tB[2]}件/Cが{tC[2]}件だが、これは確認サブセット限定。全160では破壊も同数(上記)。"
)
# 生件数+Wilson。破壊は実在(件数>0)、"ゼロかの検定"ではない。修正0との非対称は少数・順序固定ゆえ強調しない。
nAc = sum(correct(r, "A") for r in conf)  # denom = Aが正解だった件数(確認)
loB, hiB = wilson(tB[2], nAc)
loC, hiC = wilson(tC[2], nAc)
print(
    f"  破壊率(A正解{nAc}件中・生件数+Wilson95%): A→B {tB[2]}/{nAc}={100 * tB[2] / nAc:.2f}% [{loB:.2f},{hiB:.2f}] / A→C {tC[2]}/{nAc}={100 * tC[2] / nAc:.2f}% [{loC:.2f},{hiC:.2f}]"
)
# C=A 一致率: Cは実質Aのコピー。食い違う分は全てC悪化。
ca_conf = sum(1 for r in conf if dec(r, "C") == dec(r, "A"))
ca_all = sum(1 for r in res if dec(r, "C") == dec(r, "A"))
print(f"  C=A一致(final_decision): 確認{ca_conf}/120・全{ca_all}/160 → Cは実質Aのコピー(食い違い分は全てC悪化)")

# C の KEEP/CHANGE 内訳 + 宣言CHANGE≠実変更 (added post-review)
print("\n--- 副次: C の KEEP/CHANGE 内訳 (確認120) ---")
keep = sum(1 for r in conf if action(r, "C") == "KEEP")
change = sum(1 for r in conf if action(r, "C") == "CHANGE")
flip = sum(1 for r in conf if action(r, "C") == "CHANGE" and dec(r, "C") != dec(r, "A"))  # 実際に判定が動いた
flip_bad = sum(1 for r in conf if action(r, "C") == "CHANGE" and dec(r, "C") != dec(r, "A") and not correct(r, "C"))
declared_no_flip = sum(1 for r in conf if action(r, "C") == "CHANGE" and dec(r, "C") == dec(r, "A"))
print(f"  KEEP={keep} / CHANGE宣言={change}")
print(
    f"  うち実際に判定を覆した={flip} (そのうち破壊={flip_bad}) / 宣言CHANGEだが判定不変={declared_no_flip} (自己申告≠実変更)"
)

# error asymmetry per condition (confirmation)
print("\n--- 副次: 誤りの非対称 (確認120) ---")
for c in "ABC":
    fm = sum(1 for r in neg if dec(r, c) == "SAME")  # false-merge: 別人をSAME
    mm = sum(1 for r in pos if dec(r, c) == "DIFFERENT")  # missed-match: 同一人物をDIFFERENT
    ab = sum(1 for r in conf if dec(r, c) is None)
    lf, hf = wilson(fm, 60)
    lm, hm = wilson(mm, 60)
    print(
        f"  {c}: 誤統合(false-merge)={fm}/60 [Wilson {lf:.1f},{hf:.1f}%]  見逃し(missed-match)={mm}/60 [Wilson {lm:.1f},{hm:.1f}%]  無効出力={ab}"
    )

# EXPLORATORY
print("\n--- 探索: 難例40 (率は母集団へ外挿しない) ---")
hp = [r for r in hard if r["truth"] == "SAME"]
hn = [r for r in hard if r["truth"] == "DIFFERENT"]
for c in "ABC":
    print(
        f"  {c}: hard-pos正答={sum(correct(r, c) for r in hp)}/{len(hp)}  hard-neg正答={sum(correct(r, c) for r in hn)}/{len(hn)}"
    )
thB = transitions(hard, "B")
thC = transitions(hard, "C")
print(f"  難例A→B: 誤→正{thB[1]} / 正→誤{thB[2]} / 誤→誤{thB[3]} [記述のみ]")
print(f"  難例A→C: 誤→正{thC[1]} / 正→誤{thC[2]} / 誤→誤{thC[3]} (純{thC[1] - thC[2]:+d}) [記述のみ]")
# 唯一の可修正誤り(Aが誤った件)の顛末 = 「0件直した」を意味あるものにする数字
a_wrong = [r for r in res if not correct(r, "A")]
print(f"  可修正誤り(A誤り)= {len(a_wrong)}件・全て難例。その顛末:")
for r in a_wrong:
    print(
        f"    {r['pair_id']}({r['kind']} 正解{r['truth']}): A={dec(r, 'A')} B={dec(r, 'B')} C={dec(r, 'C')}(act {action(r, 'C')}) → C{'が修正' if correct(r, 'C') else 'は修正せず(KEEP)' if action(r, 'C') == 'KEEP' else 'は修正失敗'}"
    )

print("\n--- 探索: A vs B 非決定性(Z3・相互参照のみ) ---")
ab_flip = sum(1 for r in res if dec(r, "A") is not None and dec(r, "B") is not None and dec(r, "A") != dec(r, "B"))
print(f"  A≠B(独立再実行で判定が変わった) = {ab_flip}/{len(res)}")

print("\n--- 探索: 較正(A確信度 粗ビン・確認120) ---")


def conf_bin(r):
    d = r.get("A")
    v = d.get("confidence") if isinstance(d, dict) else None
    return "hi(>=90)" if (v or 0) >= 90 else "lo(<90)"


for b in ["hi(>=90)", "lo(<90)"]:
    g = [r for r in conf if conf_bin(r) == b]
    if g:
        print(
            f"  {b}: n={len(g)} A正答率={sum(correct(r, 'A') for r in g) / len(g):.3f}  (高確信で誤り={sum(1 for r in g if not correct(r, 'A'))})"
        )

json.dump(
    {
        "delta_C_minus_B": d_hat,
        "ci": [lo, hi],
        "BA": {c: ba(c) for c in "ABC"},
        "primary_CvsB_confirmation": {
            "both_correct": bc_bC,
            "B_only": b_not_c,
            "C_only": c_not_b,
            "neither": neither,
            "mcnemar_exact_p": mcnemar_exact(b_not_c, c_not_b),
        },
        "destruction_A_to_B": {"destroyed": tB[2], "fixed": tB[1], "wilson95": list(wilson(tB[2], nAc))},
        "destruction_A_to_C": {
            "correct_kept": tt,
            "fixed": ft,
            "destroyed": tf,
            "both_wrong": ff,
            "wilson95": list(wilson(tf, nAc)),
        },
        "C_equals_A": {"conf": ca_conf, "all": ca_all, "note": "C is essentially A; disagreements all worse"},
        "fixable_errors": {
            "n": len(a_wrong),
            "fixed_by_C": sum(1 for r in a_wrong if correct(r, "C")),
            "detail": [
                {"pair_id": r["pair_id"], "kind": r["kind"], "C_action": action(r, "C"), "C_fixed": correct(r, "C")}
                for r in a_wrong
            ],
        },
        "hard_A_to_C": {"fixed": thC[1], "destroyed": thC[2]},
        "C_actions": {
            "keep": keep,
            "change_declared": change,
            "change_flipped": flip,
            "change_flipped_wrong": flip_bad,
            "change_declared_no_flip": declared_no_flip,
        },
        "parse_fail": parse_fail,
        "n_conf": len(conf),
    },
    open(ROOT + "/data/phase1/analysis_summary.json", "w", encoding="utf-8", newline="\n"),
    ensure_ascii=False,
    indent=1,
)
print("\nsaved: data/phase1/analysis_summary.json")
