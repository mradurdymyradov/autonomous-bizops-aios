#!/usr/bin/env python3
"""Health-check the Sheets CRM connection. Fails loudly on the exact broken line.

Run:  python verify.py

Checks, in order:
  1. .env exists and both keys are filled
  2. service account JSON exists and parses
  3. Google accepts the credentials
  4. the service account can actually open THIS spreadsheet
  5. the three expected tabs exist with the expected headers
  6. the rows parse into leads
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
ENV = HERE / ".env"
OK, BAD = "  OK  ", " FAIL "

EXPECTED = {
    "Заявки": ["Время", "Тип", "Lead ID", "Телефон", "Вопрос", "Ответ",
               "Источник", "Вариант", "Страница"],
    # Rebuilt 2026-07-28 from the phone's call log by calls.py — one row per
    # lead, not per button tap. The old event-log header lives on in
    # «Звонки-архив», which nothing verifies because nothing reads it.
    "Звонки": ["№", "Lead ID", "Заявка", "Телефон", "Бизнес", "Instagram",
               "Креатив", "Первый звонок", "Через (мин)", "Исходящих",
               "Дозвонился"],
    "Чат-лог": ["Время", "Сессия", "Секунда", "Событие", "Детали", "Страница"],
}


def step(n, what):
    print(f"\n[{n}] {what}")


def die(msg, fix):
    print(f"{BAD} {msg}")
    print(f"       fix: {fix}")
    sys.exit(1)


def main():
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=" * 72)
    print("Sheets CRM connection check -- voronka")
    print("=" * 72)

    # 1 -----------------------------------------------------------------
    step(1, ".env file and keys")
    if not ENV.exists():
        die(f"no {ENV}", "copy .env.example to .env (both values are prefilled)")
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

    sid = env.get("SHEET_ID", "")
    if not sid or sid.startswith("<"):
        die("SHEET_ID is empty", "the id sits in the sheet URL between /d/ and /edit")
    print(f"{OK} SHEET_ID = {sid}")

    keyname = env.get("SHEETS_CREDENTIALS_JSON", "")
    if not keyname or keyname.startswith("<"):
        die("SHEETS_CREDENTIALS_JSON is empty", "point it at the service account key")
    key = Path(keyname)
    if not key.is_absolute():
        key = HERE / key

    # 2 -----------------------------------------------------------------
    step(2, "service account key file")
    if not key.exists():
        die(f"not found: {key}",
            "the shared key lives at automations/google-service-account.json. "
            "Re-download it from console.cloud.google.com > IAM > Service "
            "Accounts > voronka-reader > Keys if it is gone.")
    try:
        blob = json.loads(key.read_text(encoding="utf-8"))
    except ValueError as e:
        die(f"not valid JSON: {e}", "re-download the key file")
    if blob.get("type") != "service_account":
        die(f"type is '{blob.get('type')}', expected 'service_account'",
            "you downloaded an OAuth client secret, not a service account key")
    email = blob.get("client_email", "")
    print(f"{OK} service account: {email}")
    print(f"{OK} project: {blob.get('project_id')}")

    # 3 -----------------------------------------------------------------
    step(3, "libraries + credential load")
    try:
        from google.oauth2 import service_account
        import google.auth.transport.requests as gr
        import requests
    except ImportError as e:
        die(f"missing library: {e.name}", "pip install google-auth requests")
    try:
        creds = service_account.Credentials.from_service_account_file(
            str(key), scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
        creds.refresh(gr.Request())
    except Exception as e:  # noqa: BLE001
        die(f"Google rejected the credentials: {e}",
            "the key may have been deleted in the console, or the clock is skewed")
    print(f"{OK} token acquired")

    # 4 -----------------------------------------------------------------
    step(4, "read access to the spreadsheet")
    hdr = {"Authorization": "Bearer " + creds.token}
    url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sid}"
           "?fields=properties.title,sheets.properties.title")
    try:
        r = requests.get(url, headers=hdr, timeout=90)
    except Exception as e:  # noqa: BLE001
        die(f"could not reach sheets.googleapis.com: {e}",
            "this is usually the VPN. Retry before suspecting the setup.")
    if r.status_code == 403:
        die("PERMISSION_DENIED",
            f"open the sheet > Настройки Доступа > add {email} as "
            f"Читатель (Viewer), uncheck 'notify'. This is the step everyone forgets.")
    if r.status_code == 404:
        die("spreadsheet not found", "SHEET_ID is wrong")
    if r.status_code != 200:
        die(f"HTTP {r.status_code}: {r.text[:300]}", "unexpected -- read the body above")
    meta = r.json()
    tabs = [s["properties"]["title"] for s in meta["sheets"]]
    print(f"{OK} readable -- «{meta['properties']['title']}», tabs: {', '.join(tabs)}")

    # 5 -----------------------------------------------------------------
    step(5, "tabs and headers")
    import urllib.parse as up
    missing = [t for t in EXPECTED if t not in tabs]
    if missing:
        die(f"missing tab(s): {', '.join(missing)}",
            "the Apps Script creates them on first write of that type; "
            "see funnel/04-lead-capture.md")
    q = "&".join("ranges=" + up.quote(f"{t}!1:1") for t in EXPECTED)
    r = requests.get(
        f"https://sheets.googleapis.com/v4/spreadsheets/{sid}/values:batchGet?{q}",
        headers=hdr, timeout=90)
    for vr, tab in zip(r.json().get("valueRanges", []), EXPECTED):
        got = (vr.get("values") or [[]])[0]
        want = EXPECTED[tab]
        if got[:len(want)] != want:
            die(f"«{tab}» headers changed: {got}",
                f"expected to start with {want}. If the Apps Script changed, "
                f"update EXPECTED in verify.py and the column indexes in crm.py")
        print(f"{OK} «{tab}» headers match")

    # 6 -----------------------------------------------------------------
    step(6, "rows parse into leads")
    sys.path.insert(0, str(HERE))
    import crm
    data = crm.fetch(env, [crm.LEADS_TAB, crm.CALLS_TAB])
    leads = crm.build(data[crm.LEADS_TAB], data[crm.CALLS_TAB])
    real = [x for x in leads if not x["is_test"]]
    dated = [x for x in real if x["ts"]]
    if not leads:
        die("zero leads parsed out of the sheet",
            "either the sheet is genuinely empty, or the column order moved")
    print(f"{OK} {len(leads)} lead records ({len(real)} real, "
          f"{len(leads) - len(real)} test/probe)")
    if dated:
        print(f"{OK} range {min(x['ts'] for x in dated):%d.%m.%Y} -> "
              f"{max(x['ts'] for x in dated):%d.%m.%Y}")
    calls = sum(1 for x in real if x["reached"] is not None)
    print(f"{OK} {calls} of {len(real)} real leads have a logged call outcome")

    print("\n" + "=" * 72)
    print("ALL CHECKS PASSED. Run:  python crm.py --days 7")
    print("=" * 72)


if __name__ == "__main__":
    main()
