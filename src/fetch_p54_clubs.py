import os

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""JP-side club history from Wikidata via the ACTION API (wbgetentities) -- a different
service than WDQS/SPARQL, so it is NOT affected by the WDQS outage/rate-limit.
Output: data/phase1/wd_clubs.csv (qid,club,start,end)."""
import json, csv, time, urllib.request, urllib.parse

ROOT = _ROOT
API = "https://www.wikidata.org/w/api.php"
UA = {"User-Agent": "llm-nayose-feasibility/0.1 (research use)"}


def chunks(x, n):
    for i in range(0, len(x), n):
        yield x[i : i + n]


def wb(ids, props, extra=None):
    p = {"action": "wbgetentities", "ids": "|".join(ids), "props": props, "format": "json"}
    if extra:
        p.update(extra)
    url = API + "?" + urllib.parse.urlencode(p)
    for a in range(4):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read())[
                "entities"
            ]
        except Exception as e:
            print(f"  wb retry {a}: {type(e).__name__}", flush=True)
            time.sleep(5 * (a + 1))
    return {}


pairs = json.load(open(ROOT + "/data/phase1/pairs.json", encoding="utf-8"))
player_qids = sorted({p["jp_qid"] for p in pairs})
print(f"players: {len(player_qids)}")


def yr(quals, pid):
    try:
        return quals.get(pid, [{}])[0]["datavalue"]["value"]["time"][1:5]
    except Exception:
        return ""


by_player = {}
club_qids = set()
for batch in chunks(player_qids, 50):
    ents = wb(batch, "claims")
    for q, e in ents.items():
        lst = []
        for cl in e.get("claims", {}).get("P54", []):
            try:
                cq = cl["mainsnak"]["datavalue"]["value"]["id"]
            except Exception:
                continue
            lst.append((cq, yr(cl.get("qualifiers", {}), "P580"), yr(cl.get("qualifiers", {}), "P582")))
            club_qids.add(cq)
        by_player[q] = lst
    time.sleep(0.4)
print(f"club QIDs to label: {len(club_qids)}")
labels = {}
for batch in chunks(sorted(club_qids), 50):
    ents = wb(batch, "labels", {"languages": "en"})
    for q, e in ents.items():
        labels[q] = e.get("labels", {}).get("en", {}).get("value", q)
    time.sleep(0.4)
with open(ROOT + "/data/phase1/wd_clubs.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f)
    w.writerow(["qid", "club", "start", "end"])
    rows = 0
    for q, lst in by_player.items():
        for cq, s, e in lst:
            w.writerow([q, labels.get(cq, cq), s, e])
            rows += 1
have = sum(1 for q in player_qids if by_player.get(q))
print(f"OK: {rows} club-rows | players with >=1 P54 club: {have}/{len(player_qids)} -> wd_clubs.csv")
