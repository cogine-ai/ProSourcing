from datetime import datetime, timedelta, timezone


def _parse_task_timestamp(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


INFLIGHT_TASK_STATUSES = frozenset(
    {"pending", "running", "crawling", "reporting", "processing", "retrying", "scraping"}
)
DEFAULT_INFLIGHT_STALE_MINUTES = 20


def _is_task_activity_stale(activity_time, stale_minutes: int) -> bool:
    if not activity_time:
        return True
    now_ref = datetime.now(activity_time.tzinfo) if activity_time.tzinfo else datetime.now()
    return activity_time <= now_ref - timedelta(minutes=stale_minutes)


def should_block_batch_category(task_row, recent_limit_iso, stale_minutes=DEFAULT_INFLIGHT_STALE_MINUTES):
    st = (task_row.get("status") or "").lower()
    created_at = task_row.get("created_at") or ""
    if st in INFLIGHT_TASK_STATUSES:
        activity_time = _parse_task_timestamp(task_row.get("updated_at")) or _parse_task_timestamp(created_at)
        return not _is_task_activity_stale(activity_time, stale_minutes)
    if st == "completed" and created_at >= recent_limit_iso:
        return True
    return False


def test_active_inflight_task_is_blocked():
    recent_limit = (datetime.now() - timedelta(days=15)).isoformat()
    task = {
        "status": "crawling",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    assert should_block_batch_category(task, recent_limit) is True


def test_stale_inflight_task_is_not_blocked():
    recent_limit = (datetime.now() - timedelta(days=15)).isoformat()
    stale_updated = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    task = {
        "status": "crawling",
        "created_at": stale_updated,
        "updated_at": stale_updated,
    }
    assert should_block_batch_category(task, recent_limit) is False


def test_recent_completed_task_is_blocked():
    recent_limit = (datetime.now() - timedelta(days=15)).isoformat()
    task = {
        "status": "completed",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    assert should_block_batch_category(task, recent_limit) is True


def test_is_task_activity_stale_handles_timezone_aware_timestamps():
    recent = datetime.now(timezone.utc) - timedelta(minutes=5)
    stale = datetime.now(timezone.utc) - timedelta(minutes=45)

    assert _is_task_activity_stale(recent, DEFAULT_INFLIGHT_STALE_MINUTES) is False
    assert _is_task_activity_stale(stale, DEFAULT_INFLIGHT_STALE_MINUTES) is True


if __name__ == "__main__":
    test_active_inflight_task_is_blocked()
    test_stale_inflight_task_is_not_blocked()
    test_recent_completed_task_is_blocked()
    test_is_task_activity_stale_handles_timezone_aware_timestamps()
    print("all tests passed")
