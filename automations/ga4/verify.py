#!/usr/bin/env python3
"""Health-check the GA4 connection. Fails loudly on the exact broken line.

Run:  python verify.py

Checks, in order:
  1. .env exists and both keys are filled
  2. service account JSON exists and parses
  3. Google accepts the credentials
  4. the service account can actually read THIS property
  5. the property returns data, and generate_lead exists in it
"""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ENV = Path(__file__).parent / ".env"
OK, BAD = "  OK  ", " FAIL "


def step(n, what):
    print(f"\n[{n}] {what}")


def die(msg, fix):
    print(f"{BAD} {msg}")
    print(f"       fix: {fix}")
    sys.exit(1)


def main():
    print("=" * 72)
    print("GA4 connection check -- voronka.tm")
    print("=" * 72)

    # 1 -----------------------------------------------------------------
    step(1, ".env file and keys")
    if not ENV.exists():
        die(f"no {ENV}", "copy .env.example to .env and fill it in (README step 4)")
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

    prop = env.get("GA4_PROPERTY_ID", "")
    if not prop or prop.startswith("<"):
        die("GA4_PROPERTY_ID is empty",
            "GA4 > Admin > Property Settings > 'PROPERTY ID' (a 9-10 digit number, "
            "NOT the G-XXXXXXX measurement id). Paste it into .env")
    if not prop.replace("properties/", "").strip().isdigit():
        die(f"GA4_PROPERTY_ID='{prop}' is not numeric",
            "you probably pasted the measurement ID (G-LVK4PKT4C2). "
            "The property ID is a plain number from Admin > Property Settings")
    prop = prop.replace("properties/", "").strip()
    print(f"{OK} GA4_PROPERTY_ID = {prop}")

    keyname = env.get("GA4_CREDENTIALS_JSON", "")
    if not keyname or keyname.startswith("<"):
        die("GA4_CREDENTIALS_JSON is empty", "README step 3 creates the key file")
    key = Path(keyname)
    if not key.is_absolute():
        key = Path(__file__).parent / key
    print(f"{OK} GA4_CREDENTIALS_JSON = {key}")

    # 2 -----------------------------------------------------------------
    step(2, "service account key file")
    if not key.exists():
        die(f"not found: {key}",
            "download the JSON key from Google Cloud Console and save it there "
            "(README step 3)")
    try:
        blob = json.loads(key.read_text(encoding="utf-8"))
    except ValueError as e:
        die(f"not valid JSON: {e}", "re-download the key file")
    if blob.get("type") != "service_account":
        die(f"type is '{blob.get('type')}', expected 'service_account'",
            "you downloaded an OAuth client secret, not a service account key")
    sa_email = blob.get("client_email", "?")
    print(f"{OK} service account: {sa_email}")
    print(f"{OK} project: {blob.get('project_id')}")

    # 3 -----------------------------------------------------------------
    step(3, "libraries + credential load")
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, RunReportRequest, GetMetadataRequest)
        from google.oauth2 import service_account
    except ImportError as e:
        die(f"missing library: {e}",
            "python -m pip install google-analytics-data")
    try:
        creds = service_account.Credentials.from_service_account_file(
            str(key), scopes=["https://www.googleapis.com/auth/analytics.readonly"])
        client = BetaAnalyticsDataClient(credentials=creds)
    except Exception as e:  # noqa: BLE001
        die(f"credentials rejected: {e}", "re-download the key file")
    print(f"{OK} client built")

    # 4 -----------------------------------------------------------------
    step(4, f"read access to property {prop}")
    try:
        md = client.get_metadata(GetMetadataRequest(
            name=f"properties/{prop}/metadata"))
    except Exception as e:  # noqa: BLE001
        msg = str(e)
        if "PERMISSION_DENIED" in msg or "403" in msg:
            die("the service account cannot read this property",
                f"GA4 > Admin > Property Access Management > '+' > add\n"
                f"            {sa_email}\n"
                f"       with the 'Viewer' role. That is README step 5.")
        if "SERVICE_DISABLED" in msg or "has not been used" in msg:
            die("the Analytics Data API is not enabled on that Cloud project",
                "https://console.cloud.google.com/apis/library/"
                "analyticsdata.googleapis.com -> Enable (README step 2)")
        if "NOT_FOUND" in msg or "404" in msg:
            die(f"property {prop} does not exist",
                "check the number in GA4 > Admin > Property Settings")
        die(f"metadata read failed: {msg[:400]}", "see the message above")
    print(f"{OK} readable -- {len(md.dimensions)} dimensions, "
          f"{len(md.metrics)} metrics available")

    # 5 -----------------------------------------------------------------
    step(5, "does the property actually have data")
    start = (date.today() - timedelta(days=29)).isoformat()
    try:
        r = client.run_report(RunReportRequest(
            property=f"properties/{prop}",
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            date_ranges=[DateRange(start_date=start, end_date="today")],
            limit=50))
    except Exception as e:  # noqa: BLE001
        die(f"runReport failed: {str(e)[:400]}", "see the message above")

    events = {row.dimension_values[0].value: row.metric_values[0].value
              for row in r.rows}
    if not events:
        print(f"{BAD} no events in the last 30 days")
        print("       That is not an auth problem -- auth passed. Either the")
        print("       property is brand new or the wrong property is wired up.")
        return 1
    print(f"{OK} {len(events)} event types in the last 30 days:")
    for name, count in sorted(events.items(), key=lambda x: -int(x[1]))[:12]:
        print(f"         {name.ljust(28)} {int(count):,}")

    if "generate_lead" in events:
        print(f"\n{OK} generate_lead present ({int(events['generate_lead']):,}) "
              "-- this is the LP's real-submit event.")
        print("       It should track close to the Meta pixel Lead count.")
    else:
        print("\n  NOTE  generate_lead not seen in 30d. app.js fires it on real")
        print("        submits only, so zero submits = zero events. Not a bug")
        print("        unless you know заявки came in during this window.")

    print("\n" + "=" * 72)
    print("ALL CHECKS PASSED. Run:  python report.py --days 7")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
