import os
_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Assemble the cross-source A-prompt for each of the 160 pairs.
JP record: ja name + Wikidata P54 clubs (wd_clubs.csv).
Romaji record: dcaribou name + dcaribou transfers clubs.
=> realistic partial club overlap (different sources). Output: data/phase1/prompts.json
(+ prompt_examples.txt for eyeball). Does NOT call the API (that's run_experiment.py)."""
import json, csv, duckdb
from collections import defaultdict
ROOT=_ROOT
pairs=json.load(open(ROOT+"/data/phase1/pairs.json",encoding="utf-8"))
# JP-side clubs from Wikidata P54 cache
wd=defaultdict(list)
for r in csv.DictReader(open(ROOT+"/data/phase1/wd_clubs.csv",encoding="utf-8")):
    wd[r["qid"]].append((r["club"], r["start"], r["end"]))
# Romaji-side clubs from dcaribou transfers
con=duckdb.connect(ROOT+"/data/raw/transfermarkt-datasets.duckdb", read_only=True)
def tm_clubs(pid,k=6):
    return con.execute("""select to_club_name, min(transfer_season) s from transfers
      where player_id=? and to_club_name is not null group by to_club_name order by s limit ?""",[pid,k]).fetchall()

INSTR=("以下の2レコードが同一人物か判定してください。生年月日は与えられていません。"
 "日本語名とローマ字名の対応、およびクラブ在籍歴の整合から判断してください。"
 "2つのレコードは別々のデータベース由来で、クラブ表記や網羅範囲は完全一致とは限りません。出力は次のJSONのみ: "
 '{"final_decision":"SAME|DIFFERENT","action":"KEEP|CHANGE","confidence":0-100,'
 '"evidence_codes":["NAME_TRANSLITERATION"|"CLUB_TENURE_CONSISTENT"|"CLUB_TENURE_CONFLICT"|"LEAGUE_MATCH"]}')
def wd_line(c):
    club,s,e=c
    yr=f" ({s}–{e})" if (s or e) else ""
    return f"    - {club}{yr}"
def tm_line(c):
    club,s=c
    return f"    - {club}"+(f" ({s})" if s else "")
def rec(lbl, name, lines):
    return "\n".join([f"レコード{lbl}:", f"  氏名: {name}", "  所属クラブ歴:"]+(lines or ["    - (情報なし)"]))
def build(ja_name, jp_qid, romaji, ro_pid):
    jp=rec("A（日本語ソース）", ja_name, [wd_line(c) for c in wd.get(jp_qid,[])[:6]])
    ro=rec("B（ローマ字ソース）", romaji, [tm_line(c) for c in tm_clubs(ro_pid)])
    return f"{INSTR}\n\n{jp}\n\n{ro}"

out=[]
for p in pairs:
    prompt=build(p["jp_name"], p["jp_qid"], p["ro_name"], p["ro_pid"])
    out.append({"pair_id":p["pair_id"],"kind":p["kind"],"truth":p["truth"],
                "jp_stratum":p["jp_stratum"],"prompt_A":prompt})
json.dump(out, open(ROOT+"/data/phase1/prompts.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)

# eyeball: 1 SAME + 1 DIFFERENT + 1 HARD_NEG
ex=[]
for want in [("CONF","SAME"),("CONF","DIFFERENT"),("HARD_NEG","DIFFERENT"),("HARD","SAME")]:
    for o,p in zip(out,pairs):
        if (p["kind"],p["truth"])==want: ex.append(f"=== {o['pair_id']} {want} ===\n{o['prompt_A']}\n"); break
open(ROOT+"/data/phase1/prompt_examples.txt","w",encoding="utf-8").write("\n".join(ex))

miss=sum(1 for p in pairs if not wd.get(p["jp_qid"]))
print(f"assembled {len(out)} prompts | JP-side players lacking P54 clubs: {miss}")
print("saved: data/phase1/prompts.json , prompt_examples.txt")
