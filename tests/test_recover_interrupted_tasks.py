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


def _is_task_activity_stale(activity_time, stale_minutes: int) -> bool:
    if not activity_time:
        return True
    now_ref = datetime.now(activity_time.tzinfo) if activity_time.tzinfo else datetime.now()
    return activity_time <= now_ref - timedelta(minutes=stale_minutes)


def _task_activity_sort_key(task) -> float:
    activity_time = _parse_task_timestamp(task.get("updated_at")) or _parse_task_timestamp(task.get("created_at"))
    return activity_time.timestamp() if activity_time else 0.0


def test_is_task_activity_stale_handles_timezone_aware_timestamps():
    recent = datetime.now(timezone.utc) - timedelta(minutes=5)
    stale = datetime.now(timezone.utc) - timedelta(minutes=45)

    assert _is_task_activity_stale(recent, 30) is False
    assert _is_task_activity_stale(stale, 30) is True


def test_is_task_activity_stale_handles_naive_timestamps():
    recent = datetime.now() - timedelta(minutes=5)
    stale = datetime.now() - timedelta(minutes=45)

    assert _is_task_activity_stale(recent, 30) is False
    assert _is_task_activity_stale(stale, 30) is True


def test_task_activity_sort_key_handles_mixed_timestamp_formats():
    aware = _parse_task_timestamp("2026-03-11T21:41:40.065345+00:00")
    naive = _parse_task_timestamp("2026-03-10T21:41:40.065345")

    tasks = [
        {"updated_at": aware.isoformat()},
        {"updated_at": naive.isoformat()},
        {},
    ]

    keys = [_task_activity_sort_key(task) for task in tasks]
    assert keys[0] > keys[1] > keys[2]


def test_old_recover_logic_crashes_on_timezone_aware_timestamps():
    stale_before = datetime.now() - timedelta(minutes=30)
    activity_time = datetime.now(timezone.utc) - timedelta(minutes=45)

    crashed = False
    try:
        activity_time > stale_before
    except TypeError:
        crashed = True

    assert crashed
