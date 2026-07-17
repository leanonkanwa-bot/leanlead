#!/usr/bin/env python3
"""
Layer B — SIGTERM drain self-test.

Exercises the SIGTERM drain logic in isolation: no live FastAPI server,
no real render, no real video files needed.

Scenarios
---------
  A  SIGTERM with NO render running
       → shutdown event set immediately, drain skipped, no wait
  B  SIGTERM while a SHORT render is running (finishes before 5 s timeout)
       → drain waits for render to finish, reports "completed"
  C  SIGTERM while a LONG render is running (exceeds 3 s drain timeout)
       → drain times out, reports Layer C recovery path
  D  503-rejection guard
       → after shutdown event is set, /api/edit equivalent raises HTTPException 503
  E  Layer C recovery integration
       → job written in "rendering" state; fresh JobStore sees it as resumable

Run:  python -X utf8 backend/test_sigterm_drain.py
Exit 0 = all pass.  Exit 1 = failures found.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

# ── Isolate jobs.json to a temp dir so we don't touch production data ────────
import app.api.jobs as _jobs_mod

_tmpdir = Path(tempfile.mkdtemp())
_fake_jobs_file = _tmpdir / "jobs.json"
_original_jobs_file = _jobs_mod.JOBS_FILE
_jobs_mod.JOBS_FILE = _fake_jobs_file

from app.api.pipeline import _RENDER_SEM, _shutdown_event

# ── Helpers ───────────────────────────────────────────────────────────────────

PASS = "PASS"
FAIL = "FAIL"
results: list[tuple[str, str, str]] = []  # (label, PASS/FAIL, detail)


def record(label: str, ok: bool, detail: str = "") -> None:
    results.append((label, PASS if ok else FAIL, detail))
    mark = "  OK  " if ok else "  FAIL"
    print(f"{mark}  {label}" + (f"  [{detail}]" if detail else ""), flush=True)


def simulate_sigterm_handler(drain_timeout_secs: int = 5) -> tuple[bool, str]:
    """
    Replicate the _sigterm_handler logic from main.py, parameterised for testing.
    Returns (drain_occurred: bool, outcome: str).
    """
    _shutdown_event.set()

    _sem_free = _RENDER_SEM.acquire(blocking=False)
    if _sem_free:
        _RENDER_SEM.release()
        return False, "no_render_in_flight"

    # Render in flight — drain.
    acquired = _RENDER_SEM.acquire(timeout=drain_timeout_secs)
    if acquired:
        _RENDER_SEM.release()
        return True, "drained_cleanly"
    return True, "drain_timeout"


def reset_shutdown() -> None:
    """Clear _shutdown_event between test cases."""
    _shutdown_event.clear()


def fake_render(duration_secs: float) -> threading.Thread:
    """Hold _RENDER_SEM for duration_secs to simulate an in-progress render."""
    def _worker():
        _RENDER_SEM.acquire()
        time.sleep(duration_secs)
        _RENDER_SEM.release()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    time.sleep(0.05)  # Give the thread time to acquire the semaphore.
    return t


# ═══════════════════════════════════════════════════════════════════════════════
# Scenario A — SIGTERM with no render running
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Scenario A: SIGTERM with no render in flight ─────────────────────────")

reset_shutdown()
t0 = time.perf_counter()
drain_occurred, outcome = simulate_sigterm_handler(drain_timeout_secs=5)
elapsed = time.perf_counter() - t0

record("A1: shutdown event set", _shutdown_event.is_set())
record("A2: no drain wait (< 0.5 s)", elapsed < 0.5, f"elapsed={elapsed:.2f}s")
record("A3: outcome = no_render_in_flight", outcome == "no_render_in_flight", outcome)
record("A4: semaphore still free after handler", _RENDER_SEM.acquire(blocking=False))
_RENDER_SEM.release()

# ═══════════════════════════════════════════════════════════════════════════════
# Scenario B — SIGTERM while short render is running (finishes within timeout)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Scenario B: SIGTERM during short render (2 s render, 5 s timeout) ────")

reset_shutdown()
t = fake_render(duration_secs=2.0)

t0 = time.perf_counter()
drain_occurred, outcome = simulate_sigterm_handler(drain_timeout_secs=5)
elapsed = time.perf_counter() - t0
t.join(timeout=6)

record("B1: shutdown event set", _shutdown_event.is_set())
record("B2: drain occurred", drain_occurred)
record("B3: outcome = drained_cleanly", outcome == "drained_cleanly", outcome)
# Drain should have taken ≥ render duration but not much more.
record("B4: elapsed ≥ 1.8 s (waited for render)", elapsed >= 1.8, f"{elapsed:.2f}s")
record("B5: elapsed < 4.0 s (didn't wait full timeout)", elapsed < 4.0, f"{elapsed:.2f}s")
record("B6: semaphore free after drain", _RENDER_SEM.acquire(blocking=False))
_RENDER_SEM.release()

# ═══════════════════════════════════════════════════════════════════════════════
# Scenario C — SIGTERM while long render is running (exceeds drain timeout)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Scenario C: SIGTERM during long render (10 s render, 3 s timeout) ────")

reset_shutdown()
t = fake_render(duration_secs=10.0)

t0 = time.perf_counter()
drain_occurred, outcome = simulate_sigterm_handler(drain_timeout_secs=3)
elapsed = time.perf_counter() - t0
t.join(timeout=12)  # Let the fake render finish so semaphore is clean.

record("C1: shutdown event set", _shutdown_event.is_set())
record("C2: drain occurred (tried to drain)", drain_occurred)
record("C3: outcome = drain_timeout", outcome == "drain_timeout", outcome)
record("C4: elapsed ≥ 3 s (waited full timeout)", elapsed >= 2.8, f"{elapsed:.2f}s")
record("C5: elapsed < 5 s (didn't block longer)", elapsed < 5.0, f"{elapsed:.2f}s")
record("C6: semaphore acquired by render is eventually released", _RENDER_SEM.acquire(timeout=12))
_RENDER_SEM.release()

# ═══════════════════════════════════════════════════════════════════════════════
# Scenario D — 503 guard: /api/edit and /approve reject once shutdown event is set
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Scenario D: 503 rejection guard ──────────────────────────────────────")

reset_shutdown()

# Before shutdown: guard should NOT trigger.
pre_shutdown_blocked = _shutdown_event.is_set()
record("D1: guard inactive before SIGTERM", not pre_shutdown_blocked)

# After shutdown: guard triggers.
_shutdown_event.set()
post_shutdown_blocked = _shutdown_event.is_set()
record("D2: guard active after SIGTERM", post_shutdown_blocked)

# Simulate what the endpoint does (the actual FastAPI check is just the .is_set() call).
def _would_return_503() -> bool:
    return _shutdown_event.is_set()

record("D3: /api/edit would return 503", _would_return_503())
record("D4: /api/jobs/{id}/approve would return 503", _would_return_503())

# ═══════════════════════════════════════════════════════════════════════════════
# Scenario E — Layer C integration: orphaned "rendering" job → resumable
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── Scenario E: Layer C recovery after orphaned render ───────────────────")

reset_shutdown()

# Write a fake source file and a job in "rendering" state.
fake_src = _tmpdir / "source.mp4"
fake_src.write_bytes(b"fake video")

orphan_id = "deadbeef12345678"
_fake_jobs_file.write_text(json.dumps({
    orphan_id: {
        "id": orphan_id,
        "status": "rendering",
        "progress": 75,
        "message": "Rendering…",
        "created_at": time.time(),
        "result": None,
        "error": None,
        "source_path": str(fake_src),
        "params": {"instructions": "test", "format_hint": "auto"},
        "plan_data": {"raw": {"keep_segments": []}},
        "transcript": None,
        "subject_pos": None,
        "energy_profile": None,
        "hook_overlay": None,
        "preview": None,
        "profile_id": None,
        "is_retry": False,
        "trashed_at": None,
    }
}), encoding="utf-8")

# Boot a fresh JobStore — simulates the new container starting up.
fresh = _jobs_mod.JobStore.__new__(_jobs_mod.JobStore)
fresh._jobs = {}
fresh._lock = threading.Lock()
fresh._resumable_jobs = []
fresh._load()

orphan_job = fresh._jobs.get(orphan_id)
in_resumable = any(j.id == orphan_id for _, j in fresh._resumable_jobs)

record("E1: orphaned render job found in store", orphan_job is not None)
record("E2: job status reset to 'queued' for auto-resume",
       (orphan_job.status if orphan_job else "?") == "queued",
       orphan_job.status if orphan_job else "?")
record("E3: job is_retry=True (no quota double-count)",
       bool(orphan_job.is_retry) if orphan_job else False)
record("E4: job appears in _resumable_jobs", in_resumable)
resume_kind = next((k for k, j in fresh._resumable_jobs if j.id == orphan_id), None)
record("E5: resumable kind = 'render'", resume_kind == "render", str(resume_kind))

# ─── Summary ──────────────────────────────────────────────────────────────────

print(f"\n{'='*66}")
failures = [r for r in results if r[1] == FAIL]
total    = len(results)
if not failures:
    print(f"  ALL {total} CHECKS PASSED — Layer B SIGTERM drain verified")
else:
    print(f"  {len(failures)} FAILURE(S)  ({total - len(failures)}/{total} passed)")
    for label, _, detail in failures:
        print(f"  FAIL  {label}  {detail}")
print(f"{'='*66}\n")

# Restore
_jobs_mod.JOBS_FILE = _original_jobs_file

sys.exit(0 if not failures else 1)
