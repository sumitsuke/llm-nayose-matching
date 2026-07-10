import os
_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""A/B/C runner for the 160 pairs (gpt-5.4-mini, reasoning_effort=low).
A = initial judgment on prompt_A. B = independent re-run, byte-identical prompt. C = two-stage
review (prompt_A + A's full output as draft, KEEP/CHANGE). Logs decision/confidence/evidence/tokens.
Incremental save + resume. Does NOT run until you execute it (waits for gold sign-off + GO).
Usage: python src/run_experiment.py"""
import json, re, time
from openai import OpenAI
ROOT=_ROOT
MODEL="gpt-5.4-mini-2026-03-17"   # pinned snapshot for reproducibility
EFFORT="low"
IN_P, OUT_P = 0.75, 4.50          # USD per 1M tokens (gpt-5.4-mini)
OUT=ROOT+"/data/phase1/run_results.json"
C_SUFFIX=("\n\n初回判定（叩き台・正しいとは限らない）:\n{}\n\n"
          "上記の初回判定を独立に再監査し、KEEP か CHANGE を選んでください。変更すること自体を目的にしないでください。")
prompts=json.load(open(ROOT+"/data/phase1/prompts.json",encoding="utf-8"))
try: results=json.load(open(OUT,encoding="utf-8"))
except Exception: results=[]
done={r["pair_id"] for r in results}
client=OpenAI()
def call(text):
    for a in range(5):
        try:
            r=client.chat.completions.create(model=MODEL,messages=[{"role":"user","content":text}],reasoning_effort=EFFORT)
            u=r.usage.model_dump()
            return dict(content=r.choices[0].message.content,inp=u["prompt_tokens"],out=u["completion_tokens"],
                        reasoning=(u.get("completion_tokens_details") or {}).get("reasoning_tokens",0))
        except Exception as e:
            print(f"    retry {a}: {type(e).__name__}",flush=True); time.sleep(5*(a+1))
    raise RuntimeError("call failed after retries")
def pj(s):
    try: return json.loads(s)
    except Exception:
        m=re.search(r"\{.*\}",s,re.S)
        try: return json.loads(m.group()) if m else None
        except Exception: return None
cost=sum((t["inp"]/1e6*IN_P+t["out"]/1e6*OUT_P) for r in results for t in r["tokens"].values())
for p in prompts:
    if p["pair_id"] in done: continue
    a=call(p["prompt_A"]); b=call(p["prompt_A"]); c=call(p["prompt_A"]+C_SUFFIX.format(a["content"]))
    for x in (a,b,c): cost+=x["inp"]/1e6*IN_P+x["out"]/1e6*OUT_P
    results.append(dict(pair_id=p["pair_id"],kind=p["kind"],truth=p["truth"],
                        A=pj(a["content"]),B=pj(b["content"]),C=pj(c["content"]),
                        A_raw=a["content"],C_raw=c["content"],
                        tokens={"A":{k:a[k] for k in("inp","out","reasoning")},
                                "B":{k:b[k] for k in("inp","out","reasoning")},
                                "C":{k:c[k] for k in("inp","out","reasoning")}}))
    json.dump(results,open(OUT,"w",encoding="utf-8"),ensure_ascii=False,indent=1)
    print(f"{p['pair_id']} done ({len(results)}/{len(prompts)}) | running cost ~${cost:.3f}",flush=True)
print(f"DONE {len(results)} pairs | total cost ~${cost:.2f} | model={MODEL}")
