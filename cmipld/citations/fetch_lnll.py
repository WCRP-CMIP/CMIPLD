#!/usr/bin/env python3
"""
fetch_cmip.py
Fetch CMIP publication metadata for a given ID range.
Usage:
    python fetch_cmip.py <start> <end>
"""

import sys, json, os, time, requests

def run(start: int, end: int):
    bibtex = 'https://cmip-publications.llnl.gov/ajax/citation/{}'
    abstract = 'https://cmip-publications.llnl.gov/ajax/abstract/{}'
    moreinfo = 'https://cmip-publications.llnl.gov/ajax/moreinfo/{}'

    records, fail = {}, []

    for id in range(start, end):
        try:
            data = requests.get(bibtex.format(id), timeout=10).json()
            data.update(requests.get(abstract.format(id), timeout=10).json())
            data.update(requests.get(moreinfo.format(id), timeout=10).json())
            records[str(id)] = data
        except Exception as e:
            print(f"[{start}-{end}] ID {id} failed: {e}", flush=True)
            fail.append(id)
            time.sleep(0.5)

    os.makedirs("results", exist_ok=True)
    out_path = f"results/cmip_{start}_{end-1}.json"
    with open(out_path, "w") as f:
        json.dump({"records": records, "fail": fail}, f, indent=2)
    print(f"[{start}-{end}] Done → {out_path}", flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python fetch_cmip.py <start> <end>")
        sys.exit(1)

    start, end = map(int, sys.argv[1:3])
    run(start, end)

