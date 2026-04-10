import argparse
import json
import os
import sys

import requests
from dotenv import load_dotenv


load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Recover stale interrupted analysis tasks via the ProSourcing API.")
    parser.add_argument("--api-base", default=os.getenv("PROSOURCING_API_BASE", "http://127.0.0.1:8000"))
    parser.add_argument("--stale-minutes", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="Status to include. Repeat for multiple values. Defaults to pending/scraping/crawling/reporting/processing/retrying.",
    )
    args = parser.parse_args()

    payload = {
        "stale_minutes": args.stale_minutes,
        "dry_run": args.dry_run,
    }
    if args.limit and args.limit > 0:
        payload["limit"] = args.limit
    if args.statuses:
        payload["statuses"] = args.statuses

    url = args.api_base.rstrip("/") + "/api/tasks/recover-interrupted"
    print(f"[RECOVER] POST {url}")
    print(f"[RECOVER] Payload: {json.dumps(payload, ensure_ascii=False)}")

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] Request failed: {exc}")
        return 1

    try:
        data = response.json()
    except ValueError:
        print("[ERROR] API did not return JSON")
        print(response.text)
        return 1

    print(json.dumps(data, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
