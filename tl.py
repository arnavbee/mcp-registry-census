import json,time,urllib.request,urllib.error,ssl
from concurrent.futures import ThreadPoolExecutor
CTX=ssl.create_default_context()
def call(url,payload,sid=None):
    h={"Content-Type":"application/json","Accept":"application/json, text/event-stream",
       "User-Agent":"frontier-census/0.1 (registry liveness study; read-only)"}
    if sid: h["Mcp-Session-Id"]=sid
    req=urllib.request.Request(url,data=json.dumps(payload).encode(),method="POST",headers=h)
    with urllib.request.urlopen(req,timeout=15,context=CTX) as r:
        return r.read(200000).decode("utf-8","replace"), r.headers.get("Mcp-Session-Id")
def parse(b):
    t=b
    if b.lstrip().startswith(("event:","data:")):
        t="".join(l[5:] for l in b.splitlines() if l.startswith("data:"))
    try: return json.loads(t)
    except Exception: return None
def go(x):
    try:
        b,sid=call(x["url"],{"jsonrpc":"2.0","id":1,"method":"initialize","params":{
          "protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"frontier-census","version":"0.1"}}})
        try: call(x["url"],{"jsonrpc":"2.0","method":"notifications/initialized"},sid)
        except Exception: pass
        b2,_=call(x["url"],{"jsonrpc":"2.0","id":2,"method":"tools/list"},sid)
        j=parse(b2)
        if not isinstance(j,dict): return dict(x,tools=-1,tnote="unparseable")
        if "error" in j: return dict(x,tools=-1,tnote=str(j["error"])[:90])
        tools=(j.get("result") or {}).get("tools")
        if tools is None: return dict(x,tools=-1,tnote="no tools field")
        return dict(x,tools=len(tools),tnote=",".join(t.get("name","?") for t in tools[:6]))
    except urllib.error.HTTPError as e: return dict(x,tools=-1,tnote=f"http {e.code}")
    except Exception as e: return dict(x,tools=-1,tnote=type(e).__name__)
rows=[x for x in json.load(open("final.json")) if x["state"]=="answered"]
with ThreadPoolExecutor(max_workers=8) as ex: res=list(ex.map(go,rows))
json.dump(res,open("tools.json","w"),indent=1)
n=len(res)
err=[r for r in res if r["tools"]<0]; zero=[r for r in res if r["tools"]==0]
ok=[r for r in res if r["tools"]>0]
print(f"handshake OK: {n}")
print(f"  tools/list works, >=1 tool : {len(ok):3}  {100*len(ok)/n:.1f}%")
print(f"  tools/list works, ZERO tools: {len(zero):3}  {100*len(zero)/n:.1f}%")
print(f"  tools/list FAILS            : {len(err):3}  {100*len(err)/n:.1f}%")
from collections import Counter
print("  fail reasons:",Counter(r["tnote"][:40] for r in err).most_common(5))
print("  zero-tool examples:",[r["name"] for r in zero][:6])
