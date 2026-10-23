# verify.py : recompute every headline figure in README.md from the committed
# JSON and check it against the published value. Offline, stdlib only, no
# network, nobody's server is touched.
#
#     python3 verify.py          # prints a table, exits 1 on any mismatch
#
# The README claims "every figure can be rebuilt from the files in this repo".
# This is that claim, executable.
import json, math, statistics, sys
from collections import Counter
from urllib.parse import urlsplit

def load(p):
    with open(p) as f:
        return json.load(f)

META = lambda r: (r.get("_meta") or {}).get("io.modelcontextprotocol.registry/official") or {}
host = lambda u: (urlsplit(u).netloc or "").lower()

checks = []
def check(label, got, want, note="", kind="figure"):
    checks.append((label, got, want, note, kind))

# --- 3.2 the frame -----------------------------------------------------------
raw = load("registry_raw.json")
check("registry rows", len(raw), 24400)

active = [r for r in raw if META(r).get("status") == "active"]
check("status == active", len(active), 23940)

latest = [r for r in active if META(r).get("isLatest")]
check("+ isLatest", len(latest), 8816, "version history is 2/3 of the registry")

remote = [r for r in latest if (r.get("server") or {}).get("remotes")]
check("+ has remotes[]", len(remote), 7160, "the frame")

pool = load("pool.json")
check("pool.json rows", len(pool), 7160)

hosts = Counter(host(p["url"]) for p in pool)
check("distinct hosts in frame", len(hosts), 6283)
check("endpoints on server.smithery.ai", hosts["server.smithery.ai"], 213)

# --- 3.3 the sample ----------------------------------------------------------
sample = load("sample.json")
check("sample n", len(sample), 300)
check("distinct hosts in sample", len({host(s["url"]) for s in sample}), 286)

# --- 3.5 the retry, the check that matters -----------------------------------
# Evidence for "4 of 24 unreachable answered on a slower pass" is the diff
# between the first pass (probed.json) and the post-retry file (final.json).
probed = load("probed.json")
final = load("final.json")
check("first-pass rows", len(probed), 300)
check("first-pass unreachable", sum(1 for x in probed if x["state"] == "unreachable"), 24)

before = {x["url"]: x["state"] for x in probed}
flipped = [x for x in final
           if before.get(x["url"]) == "unreachable" and x["state"] == "answered"]
check("unreachable -> answered on retry", len(flipped), 4, "16.7% false negatives")
check("states changed by the retry",
      sum(1 for x in final if before.get(x["url"]) != x["state"]), 4,
      "the retry only ever rescued; it demoted nothing")

# --- 4.1 liveness ------------------------------------------------------------
states = Counter(x["state"] for x in final)
check("final rows", len(final), 300)
for state, want in [("answered", 155), ("auth_required", 78), ("not_mcp", 41),
                    ("unreachable", 20), ("protocol_error", 6)]:
    check(f"  {state}", states[state], want, f"{100 * states[state] / len(final):.1f}%")

broken = states["not_mcp"] + states["unreachable"] + states["protocol_error"]
check("listed active and broken", broken, 67, f"{100 * broken / len(final):.1f}%")

# --- 4.2 what the live ones expose -------------------------------------------
tools = load("tools.json")
check("handshake OK, tools/list attempted", len(tools), 155)
counts = sorted(x["tools"] for x in tools if x["tools"] > 0)
check("  exposing >= 1 tool", len(counts), 147)
check("  exposing 0 tools", sum(1 for x in tools if x["tools"] == 0), 0, "no empty shells")
check("  tools/list failed", sum(1 for x in tools if x["tools"] < 0), 8)
check("  median tools", int(statistics.median(counts)), 6)
check("  mean tools", round(sum(counts) / len(counts), 1), 10.1)
check("  90th percentile", counts[int(0.9 * len(counts))], 21)
check("  max tools", max(counts), 71)

# --- the chain ---------------------------------------------------------------
# Every check above counts rows inside one file. None of them would catch the
# failure that would matter most: a sample drawn from somewhere other than the
# stated frame, or a later file quietly covering a different set of endpoints.
# All 31 figures would still match, and they would describe a population the
# README never claimed. These are the joins between the files, so they run here,
# once every file is loaded.
sample_urls = {s["url"] for s in sample}
check("sample drawn from the frame", len(sample_urls - {p["url"] for p in pool}), 0,
      "URLs in sample.json that are not in pool.json", kind="chain")
check("sample has no repeated URL", len(sample) - len(sample_urls), 0,
      "n=300 is 300 distinct endpoints", kind="chain")
check("first pass covers the sample", {x["url"] for x in probed} == sample_urls, True,
      "probed.json is the sample, not a subset", kind="chain")
check("post-retry file covers the sample", {x["url"] for x in final} == sample_urls, True,
      "the retry added and dropped nobody", kind="chain")
check("tools.json is exactly the answered set",
      {x["url"] for x in tools} == {x["url"] for x in final if x["state"] == "answered"}, True,
      "tools/list was attempted on every server that handshook, and only those",
      kind="chain")

# --- 3.3 / 4.1 the error bars ------------------------------------------------
# The README quotes a margin on the two headline proportions. Same method it
# states: 95% Wald, times the finite-population correction for drawing n of N
# without replacement. Those margins were the only published figures this
# script could not rebuild.
N_FRAME = 7160

def moe(k, n, N=N_FRAME):
    """95% margin of error in percentage points, finite-population corrected."""
    p = k / n
    se = math.sqrt(p * (1 - p) / n) * math.sqrt((N - n) / (N - 1))
    return round(100 * 1.96 * se, 1)

check("margin on answered", moe(states["answered"], len(final)), 5.5, "pp, 95% + FPC")
check("margin on broken", moe(broken, len(final)), 4.6, "pp, 95% + FPC")
check("margin at p=0.5, n=3000", moe(1500, 3000), 1.4, "what 10x the sample would buy")

# --- report ------------------------------------------------------------------
bad = 0
seen = Counter()
for label, got, want, note, kind in checks:
    ok = got == want
    bad += not ok
    seen[kind, ok] += 1
    line = f"{'ok ' if ok else 'FAIL'}  {label:<34} {got!s:>8}"
    if not ok:
        line += f"   expected {want}" if kind == "chain" else f"   README says {want}"
    elif note:
        line += f"   {note}"
    print(line)

figs, chains = seen["figure", True], seen["chain", True]
print(f"\n{figs}/{seen['figure', True] + seen['figure', False]} figures match README.md, "
      f"{chains}/{seen['chain', True] + seen['chain', False]} chain checks pass")
sys.exit(1 if bad else 0)
