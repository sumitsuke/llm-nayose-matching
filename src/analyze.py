import os
_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Analysis per PREREGISTRATION.md. Reads run_results.json + construction_label (gold, 0 errors verified).
Primary: Delta = balanced_accuracy_C - balanced_accuracy_B on the confirmation set (120), stratified
bootstrap 95% CI (resample positives & negatives independently). Secondary: correct-destruction (A->C),
error asymmetry (false-merge vs missed-match). Exploratory: hard set, A/B non-determinism, coarse calibration.
ASCII report + data/phase1/analysis_summary.json."""
import json, random
random.seed(0)
ROOT=_ROOT
res=json.load(open(ROOT+"/data/phase1/run_results.json",encoding="utf-8"))
def dec(r,cond): d=r.get(cond); return d.get("final_decision") if isinstance(d,dict) else None
def correct(r,cond): return dec(r,cond)==r["truth"]

conf=[r for r in res if r["kind"]=="CONF"]
pos=[r for r in conf if r["truth"]=="SAME"]; neg=[r for r in conf if r["truth"]=="DIFFERENT"]
hard=[r for r in res if r["kind"] in ("HARD","HARD_NEG")]

def rate(rows,cond): return sum(correct(r,cond) for r in rows)/len(rows) if rows else float('nan')
def ba(cond,P=pos,N=neg): return 0.5*(rate(P,cond)+rate(N,cond))

print(f"=== run: {len(res)} pairs (conf {len(conf)}: pos {len(pos)}/neg {len(neg)} | hard {len(hard)}) ===")
parse_fail=sum(1 for r in res for c in "ABC" if dec(r,c) is None)
print(f"JSON parse failures (A/B/C cells): {parse_fail}/{3*len(res)}")

print("\n--- 精度(確認セット120) ---")
for c in "ABC":
    print(f"  {c}: sensitivity(SAME正答)={rate(pos,c):.3f}  specificity(DIFF正答)={rate(neg,c):.3f}  balanced_acc={ba(c):.3f}  overall={rate(conf,c):.3f}")

# PRIMARY: Delta = BA_C - BA_B, stratified bootstrap CI
def delta(P,N): return ba("C",P,N)-ba("B",P,N)
d_hat=delta(pos,neg)
B=5000; boots=[]
for _ in range(B):
    P=[random.choice(pos) for _ in pos]; N=[random.choice(neg) for _ in neg]
    boots.append(delta(P,N))
boots.sort(); lo,hi=boots[int(.025*B)],boots[int(.975*B)]
print("\n=== 主要評価項目: Delta = balanced_acc_C - balanced_acc_B (確認120) ===")
print(f"  Delta = {d_hat*100:+.1f} pt   95%CI(層化bootstrap) = [{lo*100:+.1f}, {hi*100:+.1f}] pt")
verdict=("改善(CI>0)" if lo>0 else "悪化(CI<0)" if hi<0 else "この標本では識別不能(CIが0をまたぐ)")
band = " かつ ±5pt以内=実用上小差" if (lo>-0.05 and hi<0.05) else ""
print(f"  判定: {verdict}{band}")

# per-class deltas
print(f"  参考: Δsensitivity={100*(rate(pos,'C')-rate(pos,'B')):+.1f}pt  Δspecificity={100*(rate(neg,'C')-rate(neg,'B')):+.1f}pt")

# SECONDARY: correct-destruction A->C (confirmation), per stratum
print("\n--- 副次: 正解破壊 A→C (確認120) ---")
def transitions(rows):
    tt=ft=tf=ff=0
    for r in rows:
        a,c=correct(r,"A"),correct(r,"C")
        tt+=a and c; ft+=(not a) and c; tf+=a and (not c); ff+=(not a) and (not c)
    return tt,ft,tf,ff
tt,ft,tf,ff=transitions(conf)
print(f"  正→正 {tt} / 誤→正(修正成功) {ft} / 正→誤(正解破壊) {tf} / 誤→誤 {ff}")
print(f"  純改善(誤→正 − 正→誤) = {ft-tf:+d}  | 破壊率 = {tf}/{tt+tf} (Aで正解だった中で)")
# same for B->C reference (does re-audit differ from just re-running)
print("  参考 独立再実行Bとの比較は主要Δ(上)で見る")

# error asymmetry per condition (confirmation)
print("\n--- 副次: 誤りの非対称 (確認120) ---")
for c in "ABC":
    fm=sum(1 for r in neg if dec(r,c)=="SAME")      # false-merge: 別人をSAME
    mm=sum(1 for r in pos if dec(r,c)=="DIFFERENT")  # missed-match: 同一人物をDIFFERENT
    ab=sum(1 for r in conf if dec(r,c) is None)
    print(f"  {c}: 誤統合(false-merge)={fm}/60  見逃し(missed-match)={mm}/60  無効出力={ab}")

# EXPLORATORY
print("\n--- 探索: 難例40 (率は母集団へ外挿しない) ---")
hp=[r for r in hard if r["truth"]=="SAME"]; hn=[r for r in hard if r["truth"]=="DIFFERENT"]
for c in "ABC":
    print(f"  {c}: hard-pos正答={sum(correct(r,c) for r in hp)}/{len(hp)}  hard-neg正答={sum(correct(r,c) for r in hn)}/{len(hn)}")
th=transitions(hard); print(f"  難例A→C: 誤→正{th[1]} / 正→誤{th[2]} (純{th[1]-th[2]:+d}) [記述のみ]")

print("\n--- 探索: A vs B 非決定性(Z3・相互参照のみ) ---")
flip=sum(1 for r in res if dec(r,"A") is not None and dec(r,"B") is not None and dec(r,"A")!=dec(r,"B"))
print(f"  A≠B(独立再実行で判定が変わった) = {flip}/{len(res)}")

print("\n--- 探索: 較正(A確信度 粗ビン・確認120) ---")
def conf_bin(r):
    d=r.get("A"); v=d.get("confidence") if isinstance(d,dict) else None
    return "hi(>=90)" if (v or 0)>=90 else "lo(<90)"
for b in ["hi(>=90)","lo(<90)"]:
    g=[r for r in conf if conf_bin(r)==b]
    if g: print(f"  {b}: n={len(g)} A正答率={sum(correct(r,'A') for r in g)/len(g):.3f}  (高確信で誤り={sum(1 for r in g if not correct(r,'A'))})")

json.dump({"delta_C_minus_B":d_hat,"ci":[lo,hi],"BA":{c:ba(c) for c in "ABC"},
           "destruction_A_to_C":{"correct_kept":tt,"fixed":ft,"destroyed":tf,"both_wrong":ff},
           "parse_fail":parse_fail,"n_conf":len(conf)},
          open(ROOT+"/data/phase1/analysis_summary.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("\nsaved: data/phase1/analysis_summary.json")
