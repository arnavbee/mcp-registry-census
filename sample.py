# pool.json -> sample.json : uniform draw without replacement.
# NOTE: the committed sample.json is the frozen 9 Sep 2026 draw. Re-running this
# gives a different valid sample, not the same one. Pass a seed to make yours repeatable.
import json, random, sys
n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
pool = json.load(open("pool.json"))
rng = random.Random(seed)
json.dump(rng.sample(pool, n), open("sample.json", "w"), indent=1)
print("pool", len(pool), "-> sample", n, "seed", seed)
