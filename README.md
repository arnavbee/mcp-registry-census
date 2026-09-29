# How much of the MCP registry actually answers?

A liveness census of the official Model Context Protocol (MCP) registry: one anonymous handshake
sent to a random sample of 300 hosted servers.

Arnav Singh, probe run 9 September 2026. Every figure can be rebuilt from the files in this repo.

## In 60 seconds

- The registry lists **24,400 rows**. Only **7,160** are hosted servers marked active and latest.
  The rest are old versions of the same servers, or servers you run yourself.
- I probed a uniform random **300** of those 7,160 with one MCP `initialize` request each.
  No tool was ever called and nothing was written to anyone's server.
- **51.7% (± 5.5)** answered the handshake. **26.0%** answered but want a key.
  **22.3% (± 4.6)** are listed as active and are broken, and nothing in the registry says so.
- Of the servers whose tool list came back (147), none was empty. Median 6 tools per server.
  The dead weight is at the front door, not behind it.
- The check I trust most: **4 of 24** endpoints first marked "unreachable" answered on a slower
  second pass. The harness was failing, not the servers. Every number here is after that retry.
- Limits: one moment, one vantage point (a home connection in India), remote servers only.
  Section 5 has the rest.

You can check all of it without touching anyone's server: every intermediate file is here,
and `python3 verify.py` rebuilds all 28 figures from them offline.

---

## 1. Why bother

Every "agentic web" pitch assumes a substrate: agents discover tools, connect, and call them.
MCP is the closest thing that substrate has to a directory, and the official registry is its
index. Registries are the part of any distributed system everybody cites and nobody measures.
The published count is a count of *entries*. I could not find a published count of *servers
that answer*.

The gap between those two numbers is what this census measures. One probe, one question:
does the thing at the end of the URL speak MCP right now?

## 2. Scope

The registry at `registry.modelcontextprotocol.io` lists two kinds of server:

- **local**: you run it yourself, usually over stdio (`npx`, `uvx`, a Docker image)
- **remote**: an HTTP endpoint someone else operates

**Only remote servers are in scope.** A local server has no liveness to measure from the outside;
"is the npm package still published" is a different study. This is stated up front because it caps
what the number means: this is a statement about hosted MCP endpoints, not about MCP.

## 3. Method

### 3.1 Crawl (`crawl.py`)

Page through `/v0/servers?limit=100`, following `nextCursor` to exhaustion.

```
24,400 rows
```

Each row carries a `_meta["io.modelcontextprotocol.registry/official"]` block with `status`,
`isLatest`, `publishedAt`, `updatedAt`.

### 3.2 Filter → the frame

Three filters, in order, each one defensible on its own:

| Filter | Rows left | Why |
|---|---|---|
| all rows | 24,400 | raw registry |
| `status == "active"` | 23,940 | 460 rows are explicitly `deprecated`; the registry is telling you not to use them |
| `isLatest == true` | 8,816 | the registry keeps every published version of a server; counting all of them counts the same server up to 20 times |
| has a `remotes[]` entry | **7,160** | the rest are local-only, out of scope per §2 |

**That 24,400 → 8,816 step is the first real finding, and it costs nothing to compute.** Roughly
two-thirds of the registry's apparent size is version history. Any headline that says "24,000 MCP
servers" is counting rows, not servers.

Where a server publishes several remotes, the first is taken. The frame is **7,160 endpoints,
6,283 distinct hosts**, so no single operator dominates it, though `server.smithery.ai` alone
accounts for 213.

### 3.3 Sample

**n = 300**, drawn uniformly at random without replacement from the 7,160 (`sample.json`;
positions run from index 4 to 7,145, mean gap 23.9 ≈ 7160/300, consistent with a uniform draw).
286 distinct hosts.

300 was chosen for the error bar it buys: ±5.5 points at p≈0.5 on a population of 7,160, with the
finite-population correction applied. Ten times the sample would buy ±1.7. It was not worth ten
times the traffic to other people's servers.

### 3.4 Probe (`probe.py`)

One POST per endpoint. The MCP `initialize` handshake, protocol version `2025-06-18`, empty
capabilities, honest `User-Agent`:

```
frontier-census/0.1 (registry liveness study; read-only)
```

No tool is ever called. Nothing is written. The probe reads at most 20 KB of the response and
handles both plain JSON and SSE framing (`event:` / `data:` lines), because servers legitimately
answer either way and a parser that only understands one will report the other as dead.

Each endpoint lands in exactly one of five states:

- **answered**: a `result` with a `protocolVersion`. It is an MCP server and it is up.
- **auth_required**: it spoke, and said no. 401/403, or a JSON-RPC error mentioning auth.
- **protocol_error**: spoke MCP, returned an error that is not about auth.
- **not_mcp**: HTTP answered, the body is not an MCP response (404 pages, landing pages, 530s).
- **unreachable**: no usable HTTP response at all: DNS, TLS, connection refused, timeout.

### 3.5 Retry (`probe2.py`), the part that matters

The first pass ran 12 workers with a 12-second timeout (`probed.json`). The retry ran **3 workers
with a 25-second timeout** over every row that was not already `answered` (`retry_in.json`, 149
rows); only the 24 `unreachable` ones bear on the claim below.

**4 of the 24 "unreachable" endpoints answered on the second pass.** They were never down. The
harness was. That diff is `probed.json` → `final.json`, and it is the only thing that changed:
the retry rescued four rows and demoted none. `verify.py` recomputes it.

⚠️ `retry_out.json` is the output of an earlier, partial retry pass and does **not** reproduce
`final.json` (it flips one row, not four). It is kept because it was run, but **`final.json` is
the authoritative post-retry file** and every figure below comes from it.

That is a **16.7% false-negative rate inside the one state most likely to be over-reported**, and
it is the most important check in this document, because it is the one that would have made the
headline wrong in the flattering direction. A liveness probe that fans out hard and times out fast
can get this wrong, and it is easy not to check.

All reported figures are **post-retry** (`final.json`).

### 3.6 Capability pass (`tl.py`)

For the 155 endpoints that answered, complete the handshake properly, `initialize`, then the
`notifications/initialized` notification, carrying the `Mcp-Session-Id` header forward, then call
`tools/list`.

---

## 4. Results

### 4.1 Liveness, n = 300

| State | n | share | 95% CI |
|---|---:|---:|---|
| **answered** | 155 | **51.7%** | 46.2 – 57.2 |
| auth_required | 78 | 26.0% | 21.1 – 30.9 |
| not_mcp | 41 | 13.7% | 9.9 – 17.5 |
| unreachable | 20 | 6.7% | 3.9 – 9.5 |
| protocol_error | 6 | 2.0% | n/a |

Read three ways:

- **51.7%** answer a handshake from an anonymous client.
- **26.0%** are alive but gated. They are working software; they want a key. Not failures, but
  not discoverable-and-usable either, which is what the agentic-web story assumes.
- **22.3% ± 4.6** (`not_mcp` + `unreachable` + `protocol_error`) are **listed as active, marked
  latest, and broken.** Better than one in five. Nothing in the registry warns you.

Scaled to the frame, that is roughly **1,600 dead endpoints carrying an `active` flag.**

### 4.2 What the live ones expose

Of the 155 that answered, `tools/list` succeeded on **147 (94.8%)**.

| | |
|---|---|
| servers exposing ≥1 tool | 147 / 155 |
| servers exposing 0 tools | **0** |
| median tools per server | **6** |
| mean | 10.1 |
| 90th percentile | 21 |
| max | 71 |
| `tools/list` failed | 8 (4 network, 2 unparseable, 1 × 401, 1 × 402) |

**No server that completed a handshake turned out to be an empty shell.** That was the failure mode
worth looking for, registry padding, and it is not there. The dead weight is all at the door, not
behind it. A live MCP server is a real one.

---

## 5. What this does not show

- **One probe, one moment.** 9 September 2026. A server down that minute is counted down. No
  attempt is made to separate permanent death from a bad afternoon, though §3.5 is the reason to
  believe the short-timeout version of that error has been controlled for.
- **Remote only.** Local/stdio servers are out of scope entirely.
- **From one vantage point**, a residential connection in India. Geo-blocking and regional CDN
  failure would read as `not_mcp` or `unreachable` here. Repeating from a second region is the
  obvious next pass.
- **`auth_required` is not graded.** Whether those 78 would work with a key is untested.
- **The registry is not the whole ecosystem.** Plenty of MCP servers are never listed at all. This
  measures the index, and the index is what discovery actually runs on.

## 6. Reproduce it

```bash
python3 crawl.py                    # → registry_raw.json   (24,400 rows)
python3 filter_pool.py              # → pool.json           (7,160 remote endpoints)
python3 sample.py 300 42            # → sample.json         (n = 300; the committed one
                                    #   is the frozen 9 Sep draw, seed unrecorded)
python3 probe.py sample.json probed.json
python3 probe2.py retry_in.json retry_out.json   # unreachable only, 3 workers, 25s
python3 tl.py                       # → tools.json          (tools/list over the 155)
```

Nothing above is needed to check the arithmetic. Every number in this README is recomputed from
the committed JSON, offline, by:

```bash
python3 verify.py                   # 28 figures, exits 1 on any mismatch
```

Every intermediate file is in this repo, so the numbers can be checked without re-running
anything against other people's servers. **Please prefer that.** If you do re-run: keep the
concurrency low, keep the honest User-Agent, and do not call a single tool.

## 7. Files

| File | What |
|---|---|
| `registry_raw.json` | full crawl, 24,400 rows, 24 MB |
| `pool.json` | the frame, 7,160 remote endpoints |
| `sample.json` | the n=300 draw |
| `probed.json` | first pass |
| `final.json` | **post-retry, the reported numbers** |
| `tools.json` | `tools/list` results for the 155 live servers |
| `crawl.py` `probe.py` `probe2.py` `tl.py` | the harness |

---

*Corrections welcome. If a server of yours is in `final.json` under the wrong state, open an issue
with the URL and it gets re-probed and the number republished.*
