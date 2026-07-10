import os
_ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
"""One-time cache of Wikidata ja/en labels for all eligible JP footballers with P2446.
Robust to WDQS outage / 429 (python-internal retry+backoff). Requests JSON, writes clean CSV.
Output: data/phase0/labels.csv  (columns: qid,tmId,ja,en)"""
import urllib.request, urllib.parse, time, sys, json, csv
OUT = os.path.join(_ROOT,"data/phase0/labels.csv")
EP = "https://query.wikidata.org/sparql"
Q = ("SELECT ?p ?tmId ?ja ?en WHERE {"
     " ?p wdt:P106 wd:Q937857 ; wdt:P27 wd:Q17 ; wdt:P2446 ?tmId ."
     ' ?p rdfs:label ?ja . FILTER(LANG(?ja)="ja")'
     ' OPTIONAL { ?p rdfs:label ?en . FILTER(LANG(?en)="en") } }')
url = EP + "?" + urllib.parse.urlencode({"query": Q})
req = urllib.request.Request(url, headers={
    "User-Agent": "llm-nayose-feasibility/0.1 (research use)",
    "Accept": "application/sparql-results+json"})
for attempt in range(1, 6):
    try:
        payload = json.loads(urllib.request.urlopen(req, timeout=120).read())
        rows = payload["results"]["bindings"]
        with open(OUT, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f); w.writerow(["qid", "tmId", "ja", "en"])
            for b in rows:
                w.writerow([b["p"]["value"].split("/")[-1], b["tmId"]["value"],
                            b.get("ja", {}).get("value", ""), b.get("en", {}).get("value", "")])
        print(f"OK: saved {len(rows)} label rows -> labels.csv")
        sys.exit(0)
    except urllib.error.HTTPError as e:
        wait = 65 if e.code == 429 else 20
        print(f"attempt {attempt}: HTTP {e.code}; sleeping {wait}s", flush=True); time.sleep(wait)
    except Exception as e:
        print(f"attempt {attempt}: {type(e).__name__} {e}; sleeping 20s", flush=True); time.sleep(20)
print("FAILED after retries (WDQS outage). Try again later.")
sys.exit(1)
