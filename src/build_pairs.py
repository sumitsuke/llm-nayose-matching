import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Phase 1 pair construction (v2: era-matched hard negatives) + gold-audit sheet.
- Confirmation 120: 60 SAME (market-value stratified, oversample obscure) + 60 DIFFERENT (same-surname, era-matched).
- Hard 40: 20 hard-POS (obscure layer) + 20 hard-NEG (lowest birth-year gap incl same-full-name).
Negatives now require same romaji surname AND minimal |birth-year gap| so club eras overlap (genuinely hard,
removing the 'different decade' shortcut). Truth by-construction. Each player used once.
Outputs: data/phase1/pairs.json + data/phase1/gold_audit_sheet.csv"""
import duckdb, json, csv, os
from collections import defaultdict

ROOT = _ROOT
os.makedirs(ROOT + "/data/phase1", exist_ok=True)
con = duckdb.connect(ROOT + "/data/raw/transfermarkt-datasets.duckdb", read_only=True)
L = ROOT + "/data/phase0/labels.csv"
con.execute(f"""create temp table pool as
 select p.player_id pid, p.name romaji, l.ja, l.qid, p.market_value_in_eur mv, p.url tm_url,
        try_cast(substr(cast(p.date_of_birth as varchar),1,4) as int) dob_year,
        split_part(p.name,' ',-1) surname,
        case when coalesce(p.market_value_in_eur,0)<100000 then 'obscure'
             when p.market_value_in_eur<=1000000 then 'mid' else 'famous' end stratum,
        (select count(distinct club) from (
           select from_club_name club from transfers t where t.player_id=p.player_id and from_club_name is not null
           union select to_club_name from transfers t where t.player_id=p.player_id and to_club_name is not null)) nclub
 from players p join read_csv_auto('{L}') l on try_cast(l.tmId as bigint)=p.player_id where l.ja<>'' """)
rows = con.execute(
    "select pid,romaji,ja,qid,mv,tm_url,dob_year,surname,stratum,nclub from pool where nclub>=2 order by pid"
).fetchall()
cols = ["pid", "romaji", "ja", "qid", "mv", "tm_url", "dob_year", "surname", "stratum", "nclub"]
P = [dict(zip(cols, r)) for r in rows]
by_str = {s: [p for p in P if p["stratum"] == s] for s in ("obscure", "mid", "famous")}
used = set()


def take(cands, k):
    out = []
    for p in cands:
        if p["pid"] in used:
            continue
        used.add(p["pid"])
        out.append(p)
        if len(out) == k:
            break
    return out


# --- positives (unchanged) ---
conf_same = []
for s, k in (("obscure", 24), ("mid", 24), ("famous", 12)):
    conf_same += take(by_str[s], k)
hard_pos = take([p for p in by_str["obscure"] if p["pid"] not in used], 20)

# --- era-matched same-surname negatives ---
bysn = defaultdict(list)
for p in P:
    if p["pid"] not in used and p["dob_year"]:
        bysn[p["surname"]].append(p)
cand = []  # (gap, not_same_full, a, b)
for sn, g in bysn.items():
    for i in range(len(g)):
        for j in range(i + 1, len(g)):
            gap = abs(g[i]["dob_year"] - g[j]["dob_year"])
            cand.append((gap, g[i]["romaji"] != g[j]["romaji"], g[i], g[j]))
cand.sort(key=lambda t: (t[0], t[1]))  # smallest gap first, same-full-name first within a gap
neg = []
for gap, _, a, b in cand:
    if a["pid"] in used or b["pid"] in used:
        continue
    used.add(a["pid"])
    used.add(b["pid"])
    neg.append((a, b, gap))
    if len(neg) == 80:
        break
hard_neg = neg[:20]
conf_diff = neg[20:80]


def mk(kind, truth, jp, ro):
    return dict(
        kind=kind,
        truth=truth,
        jp_pid=jp["pid"],
        jp_name=jp["ja"],
        jp_qid=jp["qid"],
        jp_url=f"https://www.wikidata.org/wiki/{jp['qid']}",
        ro_pid=ro["pid"],
        ro_name=ro["romaji"],
        ro_tm_url=ro["tm_url"],
        jp_stratum=jp["stratum"],
        ro_stratum=ro["stratum"],
    )


pairs = [mk("CONF", "SAME", p, p) for p in conf_same] + [mk("HARD", "SAME", p, p) for p in hard_pos]
pairs += [mk("CONF", "DIFFERENT", a, b) for a, b, _ in conf_diff] + [
    mk("HARD_NEG", "DIFFERENT", a, b) for a, b, _ in hard_neg
]
for i, pr in enumerate(pairs):
    pr["pair_id"] = f"P{i + 1:03d}"
json.dump(pairs, open(ROOT + "/data/phase1/pairs.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
with open(ROOT + "/data/phase1/gold_audit_sheet.csv", "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(
        [
            "pair_id",
            "kind",
            "truth_by_construction",
            "name_ja",
            "jp_wikidata_url",
            "name_latin",
            "romaji_transfermarkt_url",
            "human_verdict(SAME/DIFFERENT/UNSURE)",
            "note",
        ]
    )
    for pr in pairs:
        w.writerow(
            [
                pr["pair_id"],
                pr["kind"],
                pr["truth"],
                pr["jp_name"],
                pr["jp_url"],
                pr["ro_name"],
                pr["ro_tm_url"],
                "",
                "",
            ]
        )

import statistics as st

gaps = [g for _, _, g in neg]
print(
    f"pairs={len(pairs)} | SAME={sum(p['truth'] == 'SAME' for p in pairs)} DIFFERENT={sum(p['truth'] == 'DIFFERENT' for p in pairs)}"
)
print(
    f"neg birth-year gap: mean={st.mean(gaps):.1f} median={st.median(gaps):.0f} max={max(gaps)} | <=2yr:{sum(1 for g in gaps if g <= 2)}/80 | same-full-name:{sum(1 for a, b, _ in neg if a['romaji'] == b['romaji'])}"
)
print(f"hard_neg gap: {[g for _, _, g in hard_neg]}")
print("saved: pairs.json, gold_audit_sheet.csv")
