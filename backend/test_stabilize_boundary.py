"""
Local test for the stabilization loop — 'jamais' scenario.

Two adjacent words with 0-gap between them straddle the clip boundary.
Without the stabilization loop, snap and clamp oscillate indefinitely.
With the loop + fallback, the boundary lands at the inter-word point (16.73)
and both invariants hold.

Run with:  python backend/test_stabilize_boundary.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "app"))

from engine.pretrim import _snap_boundary_out_of_word


def _simulate_stabilization(
    planned: list[tuple],   # [(i, s_src, e, s_padded, e_padded), ...]
    wt: list[tuple],        # [(ws, we), ...]  sorted word timings
    max_passes: int = 5,
    min_dur: float = 0.030,
    gap_s: float = 0.010,
) -> tuple[list[tuple], set[int]]:
    """Simulate the snap→clamp stabilization loop from pretrim()."""
    resolved: set[int] = set()

    for pass_n in range(max_passes):
        snap_changed = False
        clamp_changed = False

        # ① snap
        for pi in range(len(planned)):
            i, s_src, e, s_i, e_pad = planned[pi]
            updated = False
            new_s, word_s = _snap_boundary_out_of_word(s_i, wt)
            if word_s:
                s_i = max(0.0, new_s)
                snap_changed = updated = True
            new_e, word_e = _snap_boundary_out_of_word(e_pad, wt)
            if word_e:
                e_pad = new_e
                snap_changed = updated = True
            if updated:
                planned[pi] = (i, s_src, e, s_i, e_pad)

        # ② clamp
        for pi in range(len(planned) - 1):
            i, s_src_i, e_i, s_i, e_pad_i = planned[pi]
            j, s_src_j, e_j, s_j, e_pad_j = planned[pi + 1]
            if e_pad_i > s_j - gap_s:
                mid = (e_pad_i + s_j) / 2.0
                planned[pi]     = (i, s_src_i, e_i, s_i, mid - 0.005)
                planned[pi + 1] = (j, s_src_j, e_j, mid + 0.005, e_pad_j)
                clamp_changed = True

        if not snap_changed and not clamp_changed:
            break
    else:
        # fallback
        for pi in range(len(planned) - 1):
            i, s_src_i, e_i, s_i, e_pad_i = planned[pi]
            j, s_src_j, e_j, s_j, e_pad_j = planned[pi + 1]
            clamp_ok = e_pad_i <= s_j - gap_s + 1e-9
            e_clean = not any(ws < e_pad_i < we for ws, we in wt if we - ws >= min_dur)
            s_clean = not any(ws < s_j < we for ws, we in wt if we - ws >= min_dur)
            if clamp_ok and e_clean and s_clean:
                continue
            bd_pt = None
            for ws, we in wt:
                if we - ws < min_dur:
                    continue
                if ws < e_pad_i < we:
                    bd_pt = we if (e_pad_i - ws >= we - e_pad_i) else ws
                    break
                if ws < s_j < we:
                    bd_pt = ws if (s_j - ws < we - s_j) else we
                    break
            gap_pt = bd_pt if bd_pt is not None else (e_pad_i + s_j) / 2.0
            planned[pi]     = (i, s_src_i, e_i, s_i, gap_pt)
            planned[pi + 1] = (j, s_src_j, e_j, gap_pt, e_pad_j)
            resolved.add(pi)

    return planned, resolved


def _assert_invariants(planned, wt, resolved):
    for pi in range(len(planned) - 1):
        i, _, _, s_i, e_pad_i = planned[pi]
        j, _, _, s_j, _ = planned[pi + 1]
        min_gap = 0.0 if pi in resolved else 0.010
        assert e_pad_i <= s_j - min_gap + 1e-9, (
            f"seg[{i}].e={e_pad_i:.3f} > seg[{j}].s - {min_gap} = {s_j - min_gap:.3f}"
        )
        for ws, we in wt:
            if ws > s_j + 0.5:
                break
            if we - ws < 0.030:
                continue
            assert not (ws < e_pad_i < we), (
                f"seg[{i}].e={e_pad_i:.3f} inside word [{ws:.3f},{we:.3f}]"
            )
            assert not (ws < s_j < we), (
                f"seg[{j}].s={s_j:.3f} inside word [{ws:.3f},{we:.3f}]"
            )


def test_clean_no_overlap():
    """No overlap, no words straddling — loop should exit on pass 0 unchanged."""
    wt = [(10.0, 10.5), (10.6, 11.0)]
    planned = [
        (0, 9.0, 10.5, 9.85, 10.65),   # e_pad = 10.65
        (1, 10.7, 11.0, 10.75, 11.10), # s = 10.75 — gap = 0.10 > 0.010 ✓
    ]
    result, resolved = _simulate_stabilization([t for t in planned], wt)
    _assert_invariants(result, wt, resolved)
    print("PASS  test_clean_no_overlap")


def test_standard_overlap_clamp():
    """Padding pushes two clips into overlap; clamp resolves without oscillation."""
    wt = [(9.0, 9.5), (10.0, 10.5), (11.0, 11.5)]
    planned = [
        (0, 8.0, 9.5, 8.85, 10.65),   # e_pad = 10.65
        (1, 10.0, 10.5, 9.85, 11.15), # s = 9.85 — overlap!
    ]
    result, resolved = _simulate_stabilization([t for t in planned], wt)
    _assert_invariants(result, wt, resolved)
    print("PASS  test_standard_overlap_clamp")


def test_jamais_adjacent_words():
    """
    The exact 'jamais' scenario: two adjacent words (0-gap) straddle the boundary.
      jamais1 = [16.02, 16.73]  (GAP-RESCUE'd into seg3)
      jamais2 = [16.73, 16.88]  (first word of seg4)
    Pass 1 snap moves e inside jamais1, clamp puts it inside jamais2, etc. — oscillation.
    Fallback must place e=s=16.73 (inter-word point) without violating either invariant.
    """
    wt = [
        (15.50, 16.02),  # some preceding word
        (16.02, 16.73),  # jamais1
        (16.73, 16.88),  # jamais2
        (16.90, 17.20),  # next word
    ]
    # seg3: e_pad = 16.75 (inside jamais2, produced by padding after word-snap of e)
    # seg4: s = 16.73 (start of jamais2)
    planned = [
        (3, 14.0, 16.73, 14.85, 16.75),  # e_pad straddles jamais2
        (4, 16.73, 17.20, 16.73, 17.35),
    ]
    result, resolved = _simulate_stabilization([t for t in planned], wt)

    # Both invariants must hold
    _assert_invariants(result, wt, resolved)

    e_final = result[0][4]
    s_final = result[1][3]
    print(f"      jamais scenario: e={e_final:.3f} s={s_final:.3f} resolved={resolved}")

    # Boundary must be at the inter-word point (16.73) or just before it
    assert e_final <= 16.73 + 1e-9, f"e_final {e_final:.3f} should be <= 16.73"
    assert s_final >= 16.73 - 1e-9, f"s_final {s_final:.3f} should be >= 16.73"
    print("PASS  test_jamais_adjacent_words")


def test_word_snap_out_of_word():
    """Unit-test _snap_boundary_out_of_word directly."""
    wt = [(1.0, 2.0), (3.0, 4.0)]

    # t before any word — no snap
    t, w = _snap_boundary_out_of_word(0.5, wt)
    assert t == 0.5 and w is None, f"expected no snap, got t={t} w={w}"

    # t inside first word, majority before → word goes to left clip → t → we + gap
    t, w = _snap_boundary_out_of_word(1.8, wt)
    assert abs(t - (2.0 + 0.010)) < 1e-9 and w == (1.0, 2.0), f"got t={t} w={w}"

    # t inside first word, majority after → word goes to right clip → t → ws - gap
    t, w = _snap_boundary_out_of_word(1.2, wt)
    assert abs(t - (1.0 - 0.010)) < 1e-9 and w == (1.0, 2.0), f"got t={t} w={w}"

    # t at word boundary (ws or we) — strict inequality, no snap
    t, w = _snap_boundary_out_of_word(1.0, wt)
    assert t == 1.0 and w is None, "t==ws should not snap"
    t, w = _snap_boundary_out_of_word(2.0, wt)
    assert t == 2.0 and w is None, "t==we should not snap"

    print("PASS  test_word_snap_out_of_word")


if __name__ == "__main__":
    test_word_snap_out_of_word()
    test_clean_no_overlap()
    test_standard_overlap_clamp()
    test_jamais_adjacent_words()
    print("\nAll tests passed.")
