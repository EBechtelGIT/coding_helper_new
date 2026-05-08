"""Tests for the GitUndoManager."""

import os
import tempfile
from pathlib import Path

from coding_agent.git_undo import GitUndoManager


def test_init_creates_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = GitUndoManager(tmpdir)
        assert (Path(tmpdir) / ".git").exists()


def test_snapshot():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = GitUndoManager(tmpdir)
        Path(tmpdir, "test.txt").write_text("hello")
        snap = mgr.snapshot("test message")
        assert snap != ""


def test_undo_redo():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = GitUndoManager(tmpdir)
        Path(tmpdir, "test.txt").write_text("v1")
        mgr.snapshot("v1")
        Path(tmpdir, "test.txt").write_text("v2")
        mgr.snapshot("v2")
        assert Path(tmpdir, "test.txt").read_text() == "v2"

        ok = mgr.undo()
        assert ok
        assert Path(tmpdir, "test.txt").read_text() == "v1"

        ok = mgr.redo()
        assert ok
        assert Path(tmpdir, "test.txt").read_text() == "v2"


def test_undo_no_changes():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = GitUndoManager(tmpdir)
        ok = mgr.undo()
        assert not ok


def test_redo_no_stack():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = GitUndoManager(tmpdir)
        ok = mgr.redo()
        assert not ok


def test_get_snapshots():
    with tempfile.TemporaryDirectory() as tmpdir:
        mgr = GitUndoManager(tmpdir)
        Path(tmpdir, "a.txt").write_text("a")
        mgr.snapshot("first")
        snapshots = mgr.get_snapshots()
        assert len(snapshots) >= 1
        assert "first" in snapshots[0]["message"]
