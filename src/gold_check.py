import os
_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""Mechanical gold verification: cross-check Wikidata DOB (P569, Action API) vs dcaribou DOB.
Handles Wikidata year-only precision and dcaribou 'YYYY-MM-DD 00:00:00' format.
- SAME  -> Wikidata DOB(jp_qid) must MATCH dcaribou DOB(ro_pid)  [ro_pid==jp_pid]
- DIFF  -> must DIFFER. Output: data/phase1/gold_verified.csv (construction_label + mechanical_gold)."""
import json, csv, time, urllib.request, urllib.parse, duckdb
ROOT=_ROOT
API="https://www.wikidata.org/w/api.php"; UA={"User-Agent":"llm-nayose/0.1 (research)"}
pairs=json.load(open(ROOT+"/data/phase1/pairs.json",encoding="utf-8"))
qids=sorted({p["jp_qid"] for p in pairs})
def chunks(x,n):
    for i in range(0,len(x),n): yield x[i:i+n]
def wb(ids):
    url=API+"?"+urllib.parse.urlencode({"action":"wbgetentities","ids":"|".join(ids),"props":"claims","format":"json"})
    for a in range(4):
        try: return json.loads(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read())["entities"]
        except Exception as e: print("  retry",a,type(e).__name__,flush=True); time.sleep(5*(a+1))
    return {}
wd_dob={}  # qid -> (date 'YYYY-MM-DD', precision)
for b in chunks(qids,50):
    for q,e in wb(b).items():
        try:
            v=e["claims"]["P569"][0]["mainsnak"]["datavalue"]["value"]
            wd_dob[q]=(v["time"][1:11], v.get("precision",11))
        except Exception: wd_dob[q]=("",0)
    time.sleep(0.4)
con=duckdb.connect(ROOT+"/data/raw/transfermarkt-datasets.duckdb", read_only=True)
pids=sorted({p["jp_pid"] for p in pairs}|{p["ro_pid"] for p in pairs})
tm_dob={r[0]:(str(r[1])[:10] if r[1] else "") for r in con.execute(
  "select player_id,date_of_birth from players where player_id in ("+",".join(map(str,pids))+")").fetchall()}

def match(wd, tm):  # wd=(date,prec) ; tm='YYYY-MM-DD'
    wdd,prec=wd
    if not wdd or not tm: return None
    year_only = prec<=9 or wdd[5:7]=="00" or wdd[8:10]=="00"
    return (wdd[:4]==tm[:4]) if year_only else (wdd==tm)

rows=[]; conf=0; nod=0; flag=[]
for p in pairs:
    wd=wd_dob.get(p["jp_qid"],("",0)); tmr=tm_dob.get(p["ro_pid"],"")
    m=match(wd,tmr)
    if p["truth"]=="SAME":
        gold = "SAME(DOB一致)" if m is True else ("要人手(DOB欠)" if m is None else "!要確認:SAMEなのにDOB不一致")
        ok = m is True
    else:
        gold = "DIFFERENT(DOB相違)" if m is False else ("要人手(DOB欠)" if m is None else "!要確認:DIFFなのにDOB一致=重複疑い")
        ok = m is False
    if m is None: nod+=1
    elif ok: conf+=1
    else: flag.append((p["pair_id"],p["kind"],p["truth"],p["jp_name"],p["ro_name"],wd[0],tmr))
    rows.append(dict(pair_id=p["pair_id"],kind=p["kind"],construction_label=p["truth"],
                     name_ja=p["jp_name"],name_latin=p["ro_name"],wikidata_qid=p["jp_qid"],
                     wd_dob=wd[0],wd_prec=wd[1],dcaribou_dob=tmr,mechanical_gold=gold))
with open(ROOT+"/data/phase1/gold_verified.csv","w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

print(f"pairs={len(pairs)} | DOBで機械的に確認={conf} | 要人手(DOB欠損)={nod} | 矛盾FLAG={len(flag)}")
for r in flag: print("  FLAG:", *r)
print("--- review高リスク(同名別人) ---")
for pid in ["P141","P142"]:
    r=next(x for x in rows if x["pair_id"]==pid)
    print(f"  {pid} {r['name_ja']}/{r['name_latin']} wd_dob={r['wd_dob']} dcaribou_dob={r['dcaribou_dob']} -> {r['mechanical_gold']}")
