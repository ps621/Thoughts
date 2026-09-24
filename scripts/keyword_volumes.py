"""Pull Keyword Planner historical search volumes for the silver-economy keyword list.

Read-only: calls KeywordPlanIdeaService.GenerateKeywordHistoricalMetrics, no account changes.

Credentials come from environment variables (GoogleAdsClient.load_from_env):
  GOOGLE_ADS_DEVELOPER_TOKEN, GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET,
  GOOGLE_ADS_REFRESH_TOKEN, GOOGLE_ADS_USE_PROTO_PLUS=True
  optional: GOOGLE_ADS_LOGIN_CUSTOMER_ID (manager account, if used)

Usage:
  pip install google-ads
  python3 scripts/keyword_volumes.py            # writes data/keyword_volumes.csv
"""
import csv
import os
import sys

from google.ads.googleads.client import GoogleAdsClient

from keywords import KEYWORDS

CID = os.environ.get("GOOGLE_ADS_CUSTOMER_ID", "1672018212")
LANGUAGE_EN = "1000"
GEOS = {"India": "2356", "US": "2840", "UK": "2826", "UAE": "2784"}



def fetch(client, geo_id, keywords):
    svc = client.get_service("KeywordPlanIdeaService")
    req = client.get_type("GenerateKeywordHistoricalMetricsRequest")
    req.customer_id = CID
    req.keywords.extend(keywords)
    req.geo_target_constants.append(f"geoTargetConstants/{geo_id}")
    req.language = f"languageConstants/{LANGUAGE_EN}"
    req.keyword_plan_network = client.enums.KeywordPlanNetworkEnum.GOOGLE_SEARCH
    resp = svc.generate_keyword_historical_metrics(request=req)
    out = {}
    for r in resp.results:
        m = r.keyword_metrics
        out[r.text] = {
            "avg_monthly": m.avg_monthly_searches,
            "competition": m.competition.name,
            "low_bid": m.low_top_of_page_bid_micros / 1e6,
            "high_bid": m.high_top_of_page_bid_micros / 1e6,
        }
        # Close variants Google folds into this keyword
        for v in r.close_variants:
            out.setdefault(v, out[r.text])
    return out


def main():
    client = GoogleAdsClient.load_from_env()
    all_kw = [k for kws in KEYWORDS.values() for k in kws]
    results = {geo: fetch(client, gid, all_kw) for geo, gid in GEOS.items()}

    os.makedirs("data", exist_ok=True)
    path = "data/keyword_volumes.csv"
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        header = ["category", "keyword"]
        for geo in GEOS:
            header += [f"{geo}_avg_monthly", f"{geo}_competition",
                       f"{geo}_low_bid", f"{geo}_high_bid"]
        w.writerow(header)
        for cat, kws in KEYWORDS.items():
            for k in kws:
                row = [cat, k]
                for geo in GEOS:
                    m = results[geo].get(k, {})
                    row += [m.get("avg_monthly", ""), m.get("competition", ""),
                            m.get("low_bid", ""), m.get("high_bid", "")]
                w.writerow(row)
    print(f"wrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
