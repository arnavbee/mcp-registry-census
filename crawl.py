import json,urllib.request,urllib.parse,time
BASE="https://registry.modelcontextprotocol.io/v0/servers"
out=[];cursor=None;pages=0
while True:
    u=BASE+"?limit=100"+(f"&cursor={urllib.parse.quote(cursor)}" if cursor else "")
    try:
        r=json.load(urllib.request.urlopen(u,timeout=30))
    except Exception as e:
        print("stop",e);break
    out+=r.get("servers",[]);pages+=1
    cursor=(r.get("metadata") or {}).get("nextCursor")
    if not cursor: break
    if pages>250: break
    time.sleep(0.05)
json.dump(out,open("registry_raw.json","w"))
print("pages",pages,"rows",len(out))
