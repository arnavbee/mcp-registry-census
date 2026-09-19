import json,sys,time,urllib.request,urllib.error,random,ssl
from concurrent.futures import ThreadPoolExecutor
CTX=ssl.create_default_context()
INIT=json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{
 "protocolVersion":"2025-06-18","capabilities":{},
 "clientInfo":{"name":"frontier-census","version":"0.1"}}}).encode()

def probe(row):
    url=row["url"]
    req=urllib.request.Request(url,data=INIT,method="POST",headers={
      "Content-Type":"application/json",
      "Accept":"application/json, text/event-stream",
      "User-Agent":"frontier-census/0.1 (registry liveness study; read-only)"})
    t=time.time()
    try:
        with urllib.request.urlopen(req,timeout=12,context=CTX) as r:
            body=r.read(20000).decode("utf-8","replace")
            code=r.status
    except urllib.error.HTTPError as e:
        code=e.code; body=e.read(4000).decode("utf-8","replace")
    except Exception as e:
        return dict(row,state="unreachable",detail=type(e).__name__+": "+str(e)[:120],ms=int((time.time()-t)*1000))
    ms=int((time.time()-t)*1000)
    # SSE framing
    txt=body
    if "data:" in body and body.lstrip().startswith(("event:","data:")):
        txt="".join(l[5:] for l in body.splitlines() if l.startswith("data:"))
    try:
        j=json.loads(txt)
    except Exception:
        return dict(row,state="not_mcp",detail=f"http {code}, unparseable",ms=ms)
    if not isinstance(j,dict):
        return dict(row,state="not_mcp",detail="non-object json",ms=ms)
    if "result" in j and isinstance(j.get("result"),dict) and "protocolVersion" in j["result"]:
        si=(j["result"].get("serverInfo") or {})
        return dict(row,state="answered",detail=si.get("name","?")+" "+str(j["result"].get("protocolVersion")),ms=ms)
    if "error" in j:
        e=j["error"]
        e=e if isinstance(e,dict) else {"message":str(e)}
        st="auth_required" if code in (401,403) or "auth" in str(e).lower() else "protocol_error"
        return dict(row,state=st,detail=str(e.get("message",""))[:120],ms=ms)
    return dict(row,state="not_mcp",detail=f"http {code}",ms=ms)

rows=json.load(open(sys.argv[1]))
with ThreadPoolExecutor(max_workers=12) as ex:
    res=list(ex.map(probe,rows))
json.dump(res,open(sys.argv[2],"w"),indent=1)
from collections import Counter
c=Counter(r["state"] for r in res)
tot=len(res)
for k,v in c.most_common(): print(f"{k:16} {v:4}  {100*v/tot:5.1f}%")
print("TOTAL",tot)
