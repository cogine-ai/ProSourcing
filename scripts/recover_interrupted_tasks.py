import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv


load_dotenv()


RUNNING_STATUSES = ["pending", "scraping", "crawling", "reporting", "processing", "retrying"]
TERMINAL_RETRY_STATUSES = {"failed", "error", "cancelled"}
DONE_STATUSES = {"completed", "failed", "error", "cancelled"}


def parse_ts(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def request_json(method, url, **kwargs):
    response = requests.request(method, url, timeout=120, **kwargs)
    try:
        data = response.json()
    except ValueError:
        data = response.text
    if response.status_code >= 400:
        raise requests.HTTPError(
            f"{response.status_code} {response.reason} for {url}: {data}",
            response=response,
        )
    return data


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def fetch_tasks_for_statuses(api_base, statuses, stale_minutes, limit):
    stale_before = datetime.now() - timedelta(minutes=max(int(stale_minutes or 0), 1))
    tasks = []
    seen = set()

    for status in statuses:
        url = api_base.rstrip("/") + "/api/tasks"
        data = request_json("GET", url, params={"status": status})
        for task in data or []:
            task_id = task.get("id")
            if not task_id or task_id in seen:
                continue
            activity_time = parse_ts(task.get("updated_at")) or parse_ts(task.get("created_at"))
            if activity_time:
                compare_now = datetime.now(activity_time.tzinfo) if activity_time.tzinfo else datetime.now()
                if activity_time > compare_now - timedelta(minutes=max(int(stale_minutes or 0), 1)):
                    continue
            elif stale_minutes:
                continue
            seen.add(task_id)
            tasks.append(task)

    tasks.sort(key=lambda task: parse_ts(task.get("updated_at")) or parse_ts(task.get("created_at")) or datetime.min)
    if limit and limit > 0:
        tasks = tasks[:limit]
    return tasks, stale_before


def get_task(api_base, task_id):
    url = api_base.rstrip("/") + f"/api/tasks/{task_id}"
    return request_json("GET", url)


def wait_for_task(api_base, task_id, poll_seconds, max_wait_minutes):
    import time

    deadline = time.time() + max_wait_minutes * 60 if max_wait_minutes and max_wait_minutes > 0 else None
    last_status = None
    while True:
        task = get_task(api_base, task_id)
        status = str(task.get("status") or "").lower()
        progress = task.get("progress")
        if status != last_status:
            print(f"[WAIT] {task_id} status={status} progress={progress}")
            last_status = status
        if status in DONE_STATUSES:
            return task
        if deadline and time.time() >= deadline:
            raise TimeoutError(f"Timed out waiting for task {task_id}; last status={status}")
        time.sleep(max(int(poll_seconds or 0), 3))


def retry_tasks_one_by_one(api_base, tasks, dry_run, poll_seconds, max_wait_minutes, stop_on_fail):
    preview = [
        {
            "id": task.get("id"),
            "category": task.get("category"),
            "category_id": task.get("category_id"),
            "status": task.get("status"),
            "updated_at": task.get("updated_at"),
            "created_at": task.get("created_at"),
        }
        for task in tasks
    ]

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "mode": "serial-retry",
            "count": len(preview),
            "tasks": preview,
        }

    finished = []
    failures = []
    for task in tasks:
        task_id = task.get("id")
        if not task_id:
            continue
        url = api_base.rstrip("/") + f"/api/tasks/{task_id}/retry"
        try:
            request_json("POST", url)
            print(f"[RETRY] queued {task_id} {task.get('category') or ''}")
            final_task = wait_for_task(api_base, task_id, poll_seconds, max_wait_minutes)
            final_status = str(final_task.get("status") or "").lower()
            finished.append({"id": task_id, "status": final_status, "category": task.get("category")})
            if final_status != "completed":
                failures.append({"id": task_id, "status": final_status, "error": final_task.get("error_msg")})
                if stop_on_fail:
                    print(f"[STOP] {task_id} ended as {final_status}; stop-on-fail is enabled.")
                    break
        except Exception as exc:
            failures.append({"id": task_id, "error": str(exc)})
            print(f"[RETRY ERROR] {task_id}: {exc}")
            if stop_on_fail:
                break

    return {
        "success": len(failures) == 0,
        "dry_run": False,
        "mode": "serial-retry",
        "count": len(finished),
        "tasks_finished": finished,
        "failures": failures,
        "tasks": preview,
    }


def main():
    parser = argparse.ArgumentParser(description="Recover stale interrupted analysis tasks via the ProSourcing API.")
    parser.add_argument("--api-base", default=os.getenv("PROSOURCING_API_BASE", "http://127.0.0.1:8000"))
    parser.add_argument("--stale-minutes", type=int, default=20)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=15)
    parser.add_argument("--max-wait-minutes", type=int, default=90)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument(
        "--mode",
        choices=["auto", "batch", "retry"],
        default="auto",
        help="auto: serial retry for terminal failed tasks, batch API for in-flight tasks; batch: only batch API; retry: only serial per-task retry.",
    )
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        help="Status to include. Repeat for multiple values. Defaults to pending/scraping/crawling/reporting/processing/retrying.",
    )
    args = parser.parse_args()

    statuses = args.statuses or RUNNING_STATUSES
    statuses = [status.strip().lower() for status in statuses if status and status.strip()]

    payload = {
        "stale_minutes": args.stale_minutes,
        "dry_run": args.dry_run,
    }
    if args.limit and args.limit > 0:
        payload["limit"] = args.limit
    if statuses:
        payload["statuses"] = statuses

    can_retry_fallback = set(statuses).issubset(TERMINAL_RETRY_STATUSES)

    use_serial_retry = args.mode == "retry" or (args.mode == "auto" and can_retry_fallback)

    if args.mode in ("auto", "batch") and not use_serial_retry:
        url = args.api_base.rstrip("/") + "/api/tasks/recover-interrupted"
        print(f"[RECOVER] POST {url}")
        print(f"[RECOVER] Payload: {json.dumps(payload, ensure_ascii=False)}")
        try:
            data = request_json("POST", url, json=payload)
            print_json(data)
            return 0
        except Exception as exc:
            print(f"[WARN] Batch recover failed: {exc}")
            if args.mode == "batch":
                return 1
            if not can_retry_fallback:
                print("[ERROR] Cannot safely fallback to per-task retry for in-flight statuses.")
                print("[HINT] For failed tasks, rerun with: --status failed")
                return 1

    if use_serial_retry:
        if not can_retry_fallback:
            print("[ERROR] Per-task retry mode only supports failed/error/cancelled statuses.")
            print("[HINT] Use batch mode for interrupted in-flight tasks.")
            return 1
        print(f"[RECOVER] Serial retry mode for statuses: {statuses}")
        try:
            tasks, stale_before = fetch_tasks_for_statuses(args.api_base, statuses, args.stale_minutes, args.limit)
        except Exception as exc:
            print(f"[ERROR] Failed to fetch task list: {exc}")
            return 1

        result = retry_tasks_one_by_one(
            args.api_base,
            tasks,
            args.dry_run,
            args.poll_seconds,
            args.max_wait_minutes,
            args.stop_on_fail,
        )
        result["stale_before"] = stale_before.isoformat()
        print_json(result)
        return 0 if result.get("success") else 1

    print("[ERROR] No recovery mode selected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
