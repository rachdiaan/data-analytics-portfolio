# -*- coding: utf-8 -*-
"""Tests for mirror_verify: every failure mode the fixture plants must be found.

    python tools/mirror-verify/tests/test_mirror_verify.py
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from mirror_verify import count_by_day, make_fixture, verify  # noqa: E402


def _build():
    tmp = tempfile.mkdtemp(prefix="mirror_verify_")
    ref = make_fixture(tmp, days=5, rows=1000)
    return tmp, ref, os.path.join(tmp, "mirror")


def test_finds_every_planted_fault():
    tmp, ref, mirror = _build()
    try:
        rep = verify(mirror, ref)
        kinds = {i.kind for i in rep.issues}
        assert not rep.ok
        # doubled day and half day both land as row-count mismatches
        assert "mismatch" in kinds, kinds
        # the day the reference does not know about must NOT pass silently
        assert "unreferenced" in kinds, kinds

        detail = " | ".join(str(i) for i in rep.issues)
        assert "looks doubled" in detail, detail
        assert "looks partial" in detail, detail
        # the orphan directory has no partition_day= in its path and is reported
        assert "(no partition_day in path)" in detail, detail
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_clean_mirror_passes():
    tmp, _, mirror = _build()
    try:
        # build the reference FROM the mirror: everything then agrees by construction,
        # which is precisely why a reference must come from the source instead
        counts = count_by_day(mirror)
        rep = verify(mirror, {"days": counts})
        assert rep.ok, str(rep)
        assert rep.days_found == rep.days_expected
        assert rep.rows_found == rep.rows_expected
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_missing_day_is_reported():
    tmp, _, mirror = _build()
    try:
        counts = count_by_day(mirror)
        counts["2026-02-09"] = 1234          # a day the source has, the mirror does not
        rep = verify(mirror, {"days": counts})
        assert any(i.kind == "missing" and i.day == "2026-02-09" for i in rep.issues)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_empty_mirror_is_not_a_pass():
    tmp = tempfile.mkdtemp(prefix="mirror_empty_")
    try:
        rep = verify(tmp, {"days": {"2026-01-01": 10}})
        assert not rep.ok
        assert rep.issues[0].kind == "missing"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok  %s" % fn.__name__)
    print("\n%d test(s) passed" % len(fns))
