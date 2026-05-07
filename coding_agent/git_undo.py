"""Git-based undo/redo functionality like OpenCode."""

import os
import subprocess
from typing import Optional, List, Dict, Any
from pathlib import Path


class GitUndoManager:
    """Manages undo/redo operations using Git."""

    def __init__(self, workdir: Optional[str] = None):
        self.workdir = workdir or os.getcwd()
        self._ensure_git_repo()

    def _ensure_git_repo(self):
        """Initialize git repo if not present."""
        git_dir = Path(self.workdir) / ".git"
        if not git_dir.exists():
            self._run_git("init")
            # Create initial commit if no commits exist
            result = self._run_git("rev-parse", "--is-inside-work-tree", check=False)
            if result.returncode != 0:
                # Create a dummy file and initial commit
                readme = Path(self.workdir) / "README.md"
                readme.write_text("# Project\n")
                self._run_git("add", ".")
                self._run_git("commit", "-m", "Initial commit")

    def _run_git(self, *args, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command."""
        return subprocess.run(
            ["git"] + list(args),
            cwd=self.workdir,
            capture_output=True,
            text=True,
            check=check,
        )

    def snapshot(self, message: str = "Agent change") -> str:
        """Create a git snapshot of current state.
        
        Returns the commit hash.
        """
        # Add all changes
        self._run_git("add", "-A")
        
        # Check if there are changes to commit
        result = self._run_git("status", "--porcelain", check=False)
        if not result.stdout.strip():
            return ""  # No changes
        
        # Commit changes
        result = self._run_git("commit", "-m", message)
        
        # Get the commit hash
        hash_result = self._run_git("rev-parse", "HEAD")
        return hash_result.stdout.strip()

    def undo(self) -> bool:
        """Undo the last change (like OpenCode's /undo).
        
        Returns True if successful.
        """
        # Check if there's anything to undo
        result = self._run_git("log", "--oneline", "-2", check=False)
        if result.returncode != 0 or not result.stdout.strip():
            return False
        
        # Get current commit
        head_result = self._run_git("rev-parse", "HEAD")
        current = head_result.stdout.strip()
        
        # Check if this is the initial commit
        parents_result = self._run_git("rev-list", "--count", "HEAD", check=False)
        if parents_result.returncode == 0 and int(parents_result.stdout.strip()) <= 1:
            # Only one commit, reset to initial state
            self._run_git("reset", "--hard", "HEAD~0")
            return True
        
        # Undo last commit but keep changes staged
        self._run_git("reset", "--soft", "HEAD~1")
        self._run_git("checkout", ".")
        
        return True

    def redo(self) -> bool:
        """Redo the last undone change.
        
        Note: Git doesn't have a native "redo". 
        We use reflog to find the commit we undid from.
        """
        # Get the reflog
        result = self._run_git("reflog", "--format=%H %gd", "-10", check=False)
        if result.returncode != 0:
            return False
        
        lines = result.stdout.strip().split('\n')
        if len(lines) < 2:
            return False
        
        # The previous HEAD before undo
        # This is a simplified implementation
        # In practice, we'd need to track the undo state
        return False  # Not fully implemented

    def get_snapshots(self) -> List[Dict[str, Any]]:
        """Get list of snapshots (commits)."""
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
        """Restore to a specific snapshot."""
        result = self._run_git("reset", "--hard", commit_hash, check=False)
        return result.returncode == 0
