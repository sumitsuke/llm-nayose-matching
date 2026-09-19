import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Phase 0 dev-20 smoke test (gpt-5.4-mini, reasoning_effort=low).
Validates: JSON stability / change-bias / pos-neg structural symmetry /
LEAK verification (grep rendered prompts for id/url/qid/digit-runs). NOT a kill gate.
Labels come from local cache data/phase0/labels.csv (no live Wikidata)."""
import json, re
import duckdb
from openai import OpenAI

ROOT = _ROOT
DB, LABELS = ROOT + "/data/raw/transfermarkt-datasets.duckdb", ROOT + "/data/phase0/labels.csv"
MODEL, EFFORT = "gpt-5.4-mini", "low"
con = duckdb.connect(DB, read_only=True)
con.execute(f"""create temp table pool as
  select p.player_id, p.name romaji, l.ja, l.qid, p.market_value_in_eur mv,
         (select count(distinct a.player_club_id) from appearances a where a.player_id=p.player_id) ncl
  from players p join read_csv_auto('{LABELS}') l on try_cast(l.tmId as bigint)=p.player_id
  where l.ja <> ''""")


def clubs(pid, k=4):
    r = con.execute(
        """select c.name,cast(min(a.date) as varchar),cast(max(a.date) as varchar),count(*) n
      from appearances a join clubs c on a.player_club_id=c.club_id
      where a.player_id=? group by c.name order by n desc limit ?""",
        [pid, k],
    ).fetchall()
    return [(x[0], x[1][:4], x[2][:4]) for x in r]


pos = con.execute("select player_id,romaji,ja,mv from pool where ncl>=2 order by coalesce(mv,0) desc").fetchall()
step = max(1, len(pos) // 10)
pos_players = pos[::step][:10]
neg = con.execute("""with b as (select player_id,romaji,ja,split_part(romaji,' ',-1) sn from pool where ncl>=2)
  select a.player_id,a.romaji,a.ja, b.player_id,b.romaji,b.ja from b a join b b on a.sn=b.sn and a.player_id<b.player_id
  limit 10""").fetchall()

INSTR = (
    "以下の2レコードが同一人物か判定してください。生年月日は与えられていません。"
    "日本語名とローマ字名の対応、およびクラブ在籍歴の整合から判断してください。出力は次のJSONのみ: "
    '{"final_decision":"SAME|DIFFERENT","action":"KEEP|CHANGE","confidence":0-100,'
    '"evidence_codes":["NAME_TRANSLITERATION"|"CLUB_TENURE_CONSISTENT"|"CLUB_TENURE_CONFLICT"|"LEAGUE_MATCH"]}'
)


def rec(lbl, name, cl):
    return "\n".join(
        [f"レコード{lbl}:", f"  氏名: {name}", "  所属クラブ歴:"]
        + ([f"    - {c} ({s}–{e})" for c, s, e in cl] or ["    - (情報なし)"])
    )


def build(nameA, clA, nameB, clB, prior=None):
    P = [INSTR, "", rec("A（日本語ソース）", nameA, clA), "", rec("B（ローマ字ソース）", nameB, clB)]
    if prior is not None:
        P += [
            "",
            "初回判定（叩き台・正しいとは限らない）:",
            prior,
            "",
            "上記を独立に再監査し KEEP か CHANGE を選べ。変更自体を目的にしないこと。",
        ]
    return "\n".join(P)


pairs = []
for pid, romaji, ja, mv in pos_players:
    cl = clubs(pid)
    pairs.append(("SAME", ja, cl, romaji, cl))
for a_pid, a_ro, a_ja, b_pid, b_ro, b_ja in neg:
    pairs.append(("DIFFERENT", a_ja, clubs(a_pid), b_ro, clubs(b_pid)))

# ---- LEAK verification on rendered prompts ----
LEAK = {
    "QID": r"\bQ\d+\b",
    "id_kw": r"player_id|spieler|transfermarkt",
    "url": r"https?://|\.r2\.dev|wikidata",
    "digits>=5": r"\d{5,}",
}
hits = {k: 0 for k in LEAK}
examples = []
for _, nA, clA, nB, clB in pairs:
    t = build(nA, clA, nB, clB)
    for k, p in LEAK.items():
        if re.search(p, t):
            hits[k] += 1
    if len(examples) < 5:
        examples.append(t)
json.dump(
    {"leak_hits": hits, "example_prompts": examples},
    open(ROOT + "/data/phase0/dev_smoke_prompts.json", "w", encoding="utf-8"),
    ensure_ascii=False,
    indent=1,
)

# ---- run A/B/C ----
client = OpenAI()


def call(t):
    r = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": t}], reasoning_effort=EFFORT)
    return r.choices[0].message.content


def pj(s):
    try:
        return json.loads(s)
    except Exception:
        m = re.search(r"\{.*\}", s, re.S)
        return json.loads(m.group()) if m else None


rows = []
for truth, nA, clA, nB, clB in pairs:
    base = build(nA, clA, nB, clB)
    a = call(base)
    b = call(base)
    c = call(build(nA, clA, nB, clB, prior=a))
    rows.append(dict(truth=truth, A=pj(a), B=pj(b), C=pj(c), A_raw=a, C_raw=c))
json.dump(rows, open(ROOT + "/data/phase0/dev_smoke_results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- report (ASCII) ----
n = len(rows)
dec = lambda x: (x or {}).get("final_decision")
parse_ok = sum(all(r[k] for k in "ABC") for r in rows)
A_acc = sum(dec(r["A"]) == r["truth"] for r in rows)
C_acc = sum(dec(r["C"]) == r["truth"] for r in rows)
pos_same = sum(dec(r["A"]) == "SAME" for r in rows if r["truth"] == "SAME")
neg_diff = sum(dec(r["A"]) == "DIFFERENT" for r in rows if r["truth"] == "DIFFERENT")
c_change = sum((r["C"] or {}).get("action") == "CHANGE" for r in rows)
ac_flip = sum(dec(r["A"]) != dec(r["C"]) for r in rows if r["A"] and r["C"])
print(
    f"MODEL={MODEL} eff={EFFORT} | pairs={n} (POS={sum(r['truth'] == 'SAME' for r in rows)}, NEG={sum(r['truth'] == 'DIFFERENT' for r in rows)})"
)
print(f"JSON parse OK (A&B&C): {parse_ok}/{n}")
print(
    f"accuracy A={A_acc}/{n} C={C_acc}/{n}  [pos->SAME {pos_same}/{sum(r['truth'] == 'SAME' for r in rows)}, neg->DIFFERENT {neg_diff}/{sum(r['truth'] == 'DIFFERENT' for r in rows)}]"
)
print(f"change-bias: C action=CHANGE {c_change}/{n} | A->C flips {ac_flip}/{n}")
print(f"LEAK scan hits: {hits}  (all 0 = no id/url/qid/long-digit leak in prompts)")
print("structure: pos/neg share one template (build fn) = symmetric by construction")
print("saved: dev_smoke_results.json / dev_smoke_prompts.json")
