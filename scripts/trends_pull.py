"""Pull Google Trends interest for the silver-economy keyword list.

Trends gives relative interest (0-100), not absolute volumes, and compares at most
5 terms per request. Every batch includes an anchor term, so scores can be rescaled
onto one common scale: score / anchor_score * 100 (anchor = 100).

Outputs (per geo):
  data/trends_<geo>.csv   keyword, category, avg interest (anchor-scaled), 5y growth %

Usage:
  pip install pytrends
  python3 scripts/trends_pull.py
"""
import os
import sys
import time

import pandas as pd
from pytrends.request import TrendReq

from keywords import KEYWORDS

GEOS = {"India": "IN", "US": "US", "UK": "GB", "UAE": "AE"}
TIMEFRAME = "today 5-y"
ANCHOR = "retirement planning"
SLEEP = 8  # Trends rate-limits hard


def pull_geo(py, geo):
    rows = []
    kws = [(cat, k) for cat, ks in KEYWORDS.items() for k in ks if k != ANCHOR]
    for i in range(0, len(kws), 4):
        batch = kws[i:i + 4]
        terms = [k for _, k in batch] + [ANCHOR]
        for attempt in range(3):
            try:
                py.build_payload(terms, timeframe=TIMEFRAME, geo=geo)
                df = py.interest_over_time()
                break
            except Exception as e:
                print(f"  retry {attempt + 1}: {e}", file=sys.stderr)
                time.sleep(SLEEP * (attempt + 2))
        else:
            df = pd.DataFrame()
        anchor_mean = df[ANCHOR].mean() if not df.empty else 0
        for cat, k in batch:
            if df.empty or k not in df or anchor_mean == 0:
                rows.append({"category": cat, "keyword": k, "interest_vs_anchor": None, "growth_5y_pct": None})
                continue
            s = df[k]
            first, last = s.iloc[:26].mean(), s.iloc[-26:].mean()  # first vs last ~6 months
            rows.append({
                "category": cat,
                "keyword": k,
                "interest_vs_anchor": round(s.mean() / anchor_mean * 100, 1),
                "growth_5y_pct": round((last - first) / first * 100, 1) if first else None,
            })
        time.sleep(SLEEP)
    return pd.DataFrame(rows).sort_values("interest_vs_anchor", ascending=False)


def main():
    os.makedirs("data", exist_ok=True)
    py = TrendReq(hl="en-US", tz=330)
    for name, code in GEOS.items():
        print(f"{name}...", file=sys.stderr)
        out = pull_geo(py, code)
        out.to_csv(f"data/trends_{name.lower()}.csv", index=False)


if __name__ == "__main__":
    main()
