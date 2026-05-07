"""Git-based undo/redo functionality like OpenCode."""

import os
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path


class GitUndoManager:
    """Manages undo/redo operations using Git."""

    def __init__(self, workdir: Optional[str] = None):
        self.workdir = workdir or os.getcwd()
        self._undo_stack: List[str] = []
        self._ensure_git_repo()

    def _ensure_git_repo(self):
        git_dir = Path(self.workdir) / ".git"
        if not git_dir.exists():
            self._run_git("init")
            result = self._run_git("rev-parse", "--is-inside-work-tree", check=False)
            if result.returncode != 0:
                readme = Path(self.workdir) / "README.md"
                if not readme.exists():
                    readme.write_text("# Project\n")
                self._run_git("add", ".")
                self._run_git("commit", "-m", "Initial commit", check=False)

    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + list(args),
            cwd=self.workdir,
            capture_output=True,
            text=True,
            check=check,
        )

    def snapshot(self, message: str = "Agent change") -> str:
        self._run_git("add", "-A")
        result = self._run_git("status", "--porcelain", check=False)
        if not result.stdout.strip():
            return ""
        self._run_git("commit", "-m", message, check=False)
        hash_result = self._run_git("rev-parse", "HEAD")
        return hash_result.stdout.strip()

    def undo(self) -> bool:
        commit_count = self._run_git("rev-list", "--count", "HEAD", check=False)
        if commit_count.returncode != 0:
            return False
        count = int(commit_count.stdout.strip())
        if count <= 1:
            return False

        current = self._run_git("rev-parse", "HEAD").stdout.strip()
        self._undo_stack.append(current)

        result = self._run_git("reset", "--hard", "HEAD~1", check=False)
        return result.returncode == 0

    def redo(self) -> bool:
        if not self._undo_stack:
            return False

        commit = self._undo_stack.pop()
        verify = self._run_git("cat-file", "-t", commit, check=False)
        if verify.returncode != 0:
            return False

        result = self._run_git("reset", "--hard", commit, check=False)
        return result.returncode == 0

    def get_snapshots(self) -> List[Dict[str, Any]]:
        result = self._run_git("log", "--oneline", "--format=%H|%s|%cr", check=False)
        if result.returncode != 0:
            return []

        snapshots = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|', 2)
            if len(parts) >= 2:
                snapshots.append({
                    'hash': parts[0],
                    'message': parts[1] if len(parts) > 1 else '',
                    'time': parts[2] if len(parts) > 2 else '',
                })

        return snapshots

    def restore_snapshot(self, commit_hash: str) -> bool:
        result = self._run_git("reset", "--hard", commit_hash, check=False)
        return result.returncode == 0