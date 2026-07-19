"""Merge duplicate profiles that share the same normalized Gmail email.

Usage:
    python backend/merge_duplicate_profiles.py            # dry-run (safe)
    python backend/merge_duplicate_profiles.py --confirm  # actually writes

Run this with the server stopped (or while no uploads are in progress)
to avoid racing with live writes to jobs.json.

Data root: DATA_DIR env var (default: storage/ relative to backend/).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths — mirrors app/core/config.py logic so no app imports needed
# ---------------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parent
_data_dir = os.environ.get("DATA_DIR", "storage")
DATA_ROOT = Path(_data_dir) if Path(_data_dir).is_absolute() else (BACKEND_DIR / _data_dir).resolve()
PROFILES_DIR = DATA_ROOT / "profiles"
JOBS_FILE = DATA_ROOT / "jobs.json"


# ---------------------------------------------------------------------------
# Email normalization (must match _normalize_email in main.py exactly)
# ---------------------------------------------------------------------------

def _normalize_email(email: str) -> str:
    email = (email or "").strip().lower()
    local, _, domain = email.partition("@")
    if not domain:
        return email
    if domain in ("gmail.com", "googlemail.com"):
        local = local.partition("+")[0]
        local = local.replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


# ---------------------------------------------------------------------------
# Plan ranking (higher index = higher tier)
# ---------------------------------------------------------------------------

_PLAN_RANK = {"free": 0, "starter": 1, "pro": 2, "agency": 3}


def _plan_rank(plan: str) -> int:
    return _PLAN_RANK.get((plan or "free").lower(), 0)


# ---------------------------------------------------------------------------
# Merge logic
# ---------------------------------------------------------------------------

def _merge_into_survivor(survivor: dict, dead_profiles: list[dict]) -> dict:
    """Return a new merged profile dict (survivor wins ties)."""
    merged = dict(survivor)

    for dead in dead_profiles:
        # Billing/Stripe: copy from dead if survivor doesn't have it
        for field in ("stripe_customer_id", "stripe_subscription_id", "billing_status", "cancel_at"):
            if not merged.get(field) and dead.get(field):
                merged[field] = dead[field]

        # Plan: take the highest-tier plan across all duplicates
        if _plan_rank(dead.get("plan", "free")) > _plan_rank(merged.get("plan", "free")):
            merged["plan"] = dead["plan"]

        # Rich profile fields: take from dead if survivor's are empty/missing
        for field in ("icp", "pillars", "platforms", "audience", "language"):
            if not merged.get(field) and dead.get(field):
                merged[field] = dead[field]

        # Nurture stamps: union — if ANY sibling sent it, mark it sent on survivor
        # (prevents re-sending emails the user already received on a dead account)
        for stamp in ("nurture_d2_sent", "nurture_d5_sent", "nurture_d10_sent", "post_render_d1_sent"):
            if dead.get(stamp) and not merged.get(stamp):
                merged[stamp] = dead[stamp]

    return merged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(dry_run: bool) -> None:
    mode_label = "DRY-RUN" if dry_run else "LIVE"
    print(f"\n{'=' * 60}")
    print(f"  merge_duplicate_profiles.py  [{mode_label}]")
    print(f"{'=' * 60}")
    print(f"  Data root : {DATA_ROOT}")
    print(f"  Profiles  : {PROFILES_DIR}")
    print(f"  Jobs file : {JOBS_FILE}")
    print()

    if not PROFILES_DIR.exists():
        print("ERROR: profiles/ directory not found. Check DATA_DIR.")
        sys.exit(1)

    # ── 1. Load all profiles ──────────────────────────────────────────────
    all_profiles: list[dict] = []
    for p_path in PROFILES_DIR.glob("*.json"):
        try:
            data = json.loads(p_path.read_text(encoding="utf-8"))
            data.setdefault("profile_id", p_path.stem)
            data["_path"] = str(p_path)
            all_profiles.append(data)
        except Exception as e:
            print(f"  WARN  skipping unreadable profile {p_path.name}: {e}")

    print(f"Loaded {len(all_profiles)} profile(s).")

    # ── 2. Group by normalized email ──────────────────────────────────────
    groups: dict[str, list[dict]] = {}
    for p in all_profiles:
        key = _normalize_email(p.get("email") or "")
        if not key or "@" not in key:
            continue
        groups.setdefault(key, []).append(p)

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if not duplicates:
        print("\nNo duplicate profiles found. Nothing to do.\n")
        return

    print(f"\nFound {len(duplicates)} duplicate group(s):\n")

    # ── 3. Plan the merges ────────────────────────────────────────────────
    merges: list[dict] = []  # list of {survivor, dead_profiles, merged}

    for norm_email, profiles in duplicates.items():
        print(f"  Email (normalized): {norm_email}")

        # Safety: never touch founder profiles
        has_founder = any(p.get("is_founder") for p in profiles)
        if has_founder:
            print(f"    SKIP — one or more profiles has is_founder=True. Touch manually.\n")
            continue

        # Sort by created_at ascending (oldest first = survivor)
        sorted_profiles = sorted(profiles, key=lambda p: float(p.get("created_at") or 0))
        survivor = sorted_profiles[0]
        dead_profiles = sorted_profiles[1:]

        for p in sorted_profiles:
            marker = "KEEP (survivor)" if p["profile_id"] == survivor["profile_id"] else "DELETE"
            created = p.get("created_at")
            created_str = time.strftime("%Y-%m-%d %H:%M", time.gmtime(created)) if created else "unknown"
            print(f"    [{marker}]  {p['profile_id']}  email={p.get('email')}  created={created_str}  plan={p.get('plan','?')}")

        merged = _merge_into_survivor(survivor, dead_profiles)
        dead_ids = {p["profile_id"] for p in dead_profiles}

        # Summarize field changes
        diffs = []
        for field in ("plan", "stripe_customer_id", "billing_status", "language", "icp"):
            old_val = survivor.get(field)
            new_val = merged.get(field)
            if old_val != new_val:
                diffs.append(f"{field}: {old_val!r} -> {new_val!r}")
        for stamp in ("nurture_d2_sent", "nurture_d5_sent", "nurture_d10_sent", "post_render_d1_sent"):
            if not survivor.get(stamp) and merged.get(stamp):
                diffs.append(f"{stamp}: (copied from duplicate)")
        if diffs:
            print(f"    Profile changes: {', '.join(diffs)}")

        # Count jobs that will be reassigned
        jobs_to_move: list[str] = []
        if JOBS_FILE.exists():
            try:
                jobs_data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
                jobs_to_move = [jid for jid, j in jobs_data.items() if j.get("profile_id") in dead_ids]
            except Exception as e:
                print(f"    WARN  could not read jobs.json: {e}")

        print(f"    Jobs to reassign: {len(jobs_to_move)}")
        print()

        merges.append({
            "survivor": survivor,
            "dead_profiles": dead_profiles,
            "dead_ids": dead_ids,
            "merged": merged,
        })

    if not merges:
        print("No eligible merges (all skipped). Exiting.\n")
        return

    if dry_run:
        print("-" * 60)
        print("DRY-RUN complete — no files written.")
        print("Re-run with --confirm to apply the changes above.")
        print()
        return

    # ── 4. Apply merges ───────────────────────────────────────────────────
    print("=" * 60)
    print("Applying merges...")
    print()

    # Reload jobs.json once
    jobs_data: dict = {}
    if JOBS_FILE.exists():
        try:
            jobs_data = json.loads(JOBS_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  WARN  could not load jobs.json: {e}")

    all_dead_ids: set[str] = set()

    for m in merges:
        survivor = m["survivor"]
        dead_profiles = m["dead_profiles"]
        dead_ids = m["dead_ids"]
        merged = m["merged"]
        norm_email = _normalize_email(survivor.get("email") or "")

        # Write updated survivor profile (strip internal _path key)
        out = {k: v for k, v in merged.items() if k != "_path"}
        survivor_path = Path(survivor["_path"])
        survivor_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  WROTE  {survivor_path.name}  (survivor for {norm_email})")

        # Reassign jobs
        moved = 0
        for jid, job in jobs_data.items():
            if job.get("profile_id") in dead_ids:
                job["profile_id"] = survivor["profile_id"]
                moved += 1
        if moved:
            print(f"  JOBS   reassigned {moved} job(s) to {survivor['profile_id']}")

        # Delete dead profile files
        for dead in dead_profiles:
            dead_path = Path(dead["_path"])
            try:
                dead_path.unlink()
                print(f"  DELETE {dead_path.name}  ({dead['profile_id']})")
            except Exception as e:
                print(f"  ERROR  could not delete {dead_path.name}: {e}")

        all_dead_ids |= dead_ids

    # Write jobs.json atomically
    if jobs_data and all_dead_ids:
        tmp = JOBS_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(jobs_data), encoding="utf-8")
        tmp.replace(JOBS_FILE)
        print(f"\n  WROTE  {JOBS_FILE.name}  (jobs.json updated)")

    print()
    print("Done. Restart the server to pick up the changes.")
    print()


if __name__ == "__main__":
    dry_run = "--confirm" not in sys.argv
    main(dry_run=dry_run)
