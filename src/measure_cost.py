import os
_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Phase 0 cost measurement: build real pairs from the 834 pool, run A/B/C on
gpt-5.4-mini, measure ACTUAL tokens (incl. reasoning) and extrapolate full-run cost.
Reports in ASCII to avoid console mojibake; prompt content is Japanese (sent to API)."""
import json, urllib.request, urllib.parse, statistics as st
import duckdb
from openai import OpenAI

DB = os.path.join(_ROOT,"data/raw/transfermarkt-datasets.duckdb")
CSV = os.path.join(_ROOT,"data/phase0/wikidata_jp_p2446.csv")
OUT = os.path.join(_ROOT,"data/phase0/cost_measure_raw.json")
MODEL = "gpt-5.4-mini"
EFFORT = "low"          # pinned per plan; None = no reasoning tokens
con = duckdb.connect(DB, read_only=True)

# --- pool = dcaribou players whose player_id is a Wikidata P2446 value; map to QID ---
con.execute(f"""
create temp table pool as
select p.player_id, p.name, p.market_value_in_eur mv,
       replace(w.p,'http://www.wikidata.org/entity/','') qid
from players p
join read_csv_auto('{CSV}') w on try_cast(w.tmId as bigint)=p.player_id
""")

def clubs(pid, k=4):
    rows = con.execute("""
      select c.name, cast(min(a.date) as varchar), cast(max(a.date) as varchar), count(*) n
      from appearances a join clubs c on a.player_club_id=c.club_id
      where a.player_id=? group by c.name order by n desc limit ?""", [pid, k]).fetchall()
    return [(r[0], r[1][:4], r[2][:4]) for r in rows]

# pick 4 players spanning market value, each with >=2 clubs, for positive pairs
cands = con.execute("""
  select pl.player_id, pl.name, pl.mv, pl.qid
  from pool pl
  where (select count(distinct a.player_club_id) from appearances a where a.player_id=pl.player_id) >= 2
  order by coalesce(pl.mv,0) desc""").fetchall()
# spread: high, mid, mid, low-ish
pos_players = [cands[0], cands[len(cands)//3], cands[2*len(cands)//3], cands[-1]]

# hard negative: two DIFFERENT pool players sharing a romaji surname
neg = con.execute("""
  with base as (select player_id,name,mv,qid, split_part(name,' ',-1) surname from pool)
  select a.player_id,a.name,a.mv,a.qid, b.player_id,b.name,b.mv,b.qid
  from base a join base b on a.surname=b.surname and a.player_id<b.player_id
  where (select count(distinct x.player_club_id) from appearances x where x.player_id=a.player_id)>=2
    and (select count(distinct y.player_club_id) from appearances y where y.player_id=b.player_id)>=2
  limit 2""").fetchall()

# --- ja labels for all involved QIDs via Wikidata SPARQL ---
qids = set(p[3] for p in pos_players)
for r in neg: qids |= {r[3], r[7]}
vals = " ".join(f"wd:{q}" for q in qids)
q = f'SELECT ?p ?ja WHERE {{ VALUES ?p {{ {vals} }} ?p rdfs:label ?ja. FILTER(LANG(?ja)="ja") }}'
url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": q, "format": "json"})
req = urllib.request.Request(url, headers={"User-Agent": "llm-nayose/0.1", "Accept": "application/sparql-results+json"})
ja = {}
for b in json.load(urllib.request.urlopen(req, timeout=60))["results"]["bindings"]:
    ja[b["p"]["value"].split("/")[-1]] = b["ja"]["value"]

INSTR = ("以下の2レコードが同一人物か判定してください。生年月日は与えられていません。"
 "日本語名とローマ字名の対応、およびクラブ在籍歴の整合から判断してください。"
 "出力は次のJSONのみ（前後に他の文字を付けない）: "
 '{"final_decision":"SAME|DIFFERENT","action":"KEEP|CHANGE","confidence":0-100,'
 '"evidence_codes":["NAME_TRANSLITERATION"|"CLUB_TENURE_CONSISTENT"|"CLUB_TENURE_CONFLICT"|"LEAGUE_MATCH"]}')
def rec(lbl, name, cl):
    L = [f"レコード{lbl}:", f"  氏名: {name}", "  所属クラブ歴:"]
    L += [f"    - {c} ({s}–{e})" for c, s, e in cl] or ["    - (情報なし)"]
    return "\n".join(L)
def prompt(nameA, clA, nameB, clB, prior=None):
    P = [INSTR, "", rec("A（日本語ソース）", nameA, clA), "", rec("B（ローマ字ソース）", nameB, clB)]
    if prior is not None:
        P += ["", "初回判定（叩き台・正しいとは限らない）:", prior,
              "", "上記の初回判定を独立に再監査し、KEEP か CHANGE を選んでください。変更自体を目的にしないこと。"]
    return "\n".join(P)

# build pairs: (label, prompt_fields) ; positives use same player's clubs on both sides
pairs = []
for pid, name, mv, qid in pos_players:
    cl = clubs(pid)
    pairs.append(("POS", ja.get(qid, name), cl, name, cl))
for r in neg:
    a_pid,a_name,a_mv,a_qid, b_pid,b_name,b_mv,b_qid = r
    pairs.append(("NEG", ja.get(a_qid, a_name), clubs(a_pid), b_name, clubs(b_pid)))

client = OpenAI()
def call(text, prior=False):
    kw = dict(model=MODEL, messages=[{"role": "user", "content": text}])
    if EFFORT: kw["reasoning_effort"] = EFFORT
    r = client.chat.completions.create(**kw)
    u = r.usage
    d = u.model_dump()
    return dict(inp=d["prompt_tokens"], out=d["completion_tokens"],
                reason=(d.get("completion_tokens_details") or {}).get("reasoning_tokens", 0),
                content=r.choices[0].message.content)

log = {"A": [], "B": [], "C": []}
raw = []
for kind, nameA, clA, nameB, clB in pairs:
    base = prompt(nameA, clA, nameB, clB)
    a = call(base)                                   # A: initial (temp default here; plan pins temp0 for real run)
    b = call(base)                                   # B: independent re-run, byte-identical
    c = call(prompt(nameA, clA, nameB, clB, prior=a["content"]))  # C: with A's draft
    for cond, x in (("A", a), ("B", b), ("C", c)):
        log[cond].append(x); raw.append({"kind": kind, "cond": cond, **{k: x[k] for k in ("inp","out","reason")}, "content": x["content"]})

json.dump(raw, open(OUT, "w"), ensure_ascii=False, indent=1)

def avg(xs): return sum(xs)/len(xs)
print(f"MODEL={MODEL} effort={EFFORT} | pairs={len(pairs)} (POS={sum(1 for p in pairs if p[0]=='POS')}, NEG={sum(1 for p in pairs if p[0]=='NEG')}) | calls={len(raw)}")
allin = allout = 0
for cond in ("A", "B", "C"):
    i = avg([x["inp"] for x in log[cond]]); o = avg([x["out"] for x in log[cond]]); rz = avg([x["reason"] for x in log[cond]])
    print(f"  {cond}: in~{i:.0f}  out~{o:.0f} (reasoning~{rz:.0f})  n={len(log[cond])}")
per_in = avg([x["inp"] for x in raw]); per_out = avg([x["out"] for x in raw])
print(f"  per-call avg: in~{per_in:.0f}  out~{per_out:.0f}")

# --- extrapolate to full run ---
CALLS = 620
tot_in = per_in*CALLS; tot_out = per_out*CALLS
print(f"\nFULL RUN extrapolation (@{CALLS} calls): input~{tot_in/1e6:.3f}M  output~{tot_out/1e6:.3f}M tokens")
PRICES = {"gpt-5.4-mini": (0.75, 4.50), "gpt-5.4-nano": (0.20, 1.25), "gpt-5.6-luna(proj)": (1.00, 6.00), "gpt-5.4": (2.50, 15.0)}
for m, (pi, po) in PRICES.items():
    cost = tot_in/1e6*pi + tot_out/1e6*po
    print(f"  {m:22s} (${pi}/{po} per 1M):  ${cost:.2f}  (dev-20 ~1/10 = ${cost/10:.2f})")
print("\nsample outputs:", [r["content"][:60] for r in raw[:3]])
