# registry_raw.json -> pool.json : the frame for the census.
# active + isLatest + has a remote endpoint. First remote wins.
import json
M = lambda r: (r.get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {}
raw = json.load(open("registry_raw.json"))
pool = []
for r in raw:
    m, s = M(r), r.get("server") or {}
    if m.get("status") != "active" or not m.get("isLatest"):
        continue
    rem = s.get("remotes") or []
    if not rem:
        continue
    pool.append({"name": s.get("name"), "url": rem[0].get("url"),
                 "type": rem[0].get("type"),
                 "published": (m.get("publishedAt") or "")[:10],
                 "updated": (m.get("updatedAt") or "")[:10]})
json.dump(pool, open("pool.json", "w"))
print("raw", len(raw), "-> pool", len(pool))
