"""Git-based undo/redo using GitPython (no subprocess)."""

import os
from pathlib import Path
from typing import Optional

import git
from git import Repo, InvalidGitRepositoryError


class GitUndoManager:
    """Manages undo/redo operations using GitPython."""

    def __init__(self, workdir: Optional[str] = None):
        self.workdir = workdir or os.getcwd()
        self._undo_stack: list[str] = []
        self._repo: Optional[Repo] = None
        self._ensure_repo()

    def _ensure_repo(self):
        try:
            self._repo = Repo(self.workdir, search_parent_directories=True)
        except InvalidGitRepositoryError:
            self._repo = Repo.init(self.workdir)
            readme = Path(self.workdir) / "README.md"
            if not readme.exists():
                readme.write_text("# Project\n")
            self._repo.index.add([str(p.relative_to(self.workdir)) for p in Path(self.workdir).iterdir() if p.is_file()])
            self._repo.index.commit("Initial commit")

    def snapshot(self, message: str = "Agent change") -> str:
        repo = self._repo
        if not repo:
            return ""

        if repo.is_dirty(untracked_files=True):
            repo.index.add("*")
            repo.index.commit(message)

        commit_hash = repo.head.commit.hexsha
        return commit_hash

    def undo(self) -> bool:
        repo = self._repo
        if not repo:
            return False

        commit_count = sum(1 for _ in repo.iter_commits())
        if commit_count <= 1:
            return False

        current = repo.head.commit.hexsha
        self._undo_stack.append(current)

        repo.head.reset(f"HEAD~1", index=True, working_tree=True)
        return True

    def redo(self) -> bool:
        if not self._undo_stack:
            return False

        commit = self._undo_stack.pop()
        repo = self._repo
        if not repo:
            return False

        try:
            repo.head.reset(commit, index=True, working_tree=True)
            return True
        except Exception:
            return False

    def get_snapshots(self) -> list[dict]:
        repo = self._repo
        if not repo:
            return []

        snapshots = []
        for commit in repo.iter_commits():
            snapshots.append({
                "hash": commit.hexsha,
                "message": commit.message.strip(),
                "time": commit.committed_datetime.strftime("%Y-%m-%d %H:%M"),
            })
        return snapshots

    def restore_snapshot(self, commit_hash: str) -> bool:
        repo = self._repo
        if not repo:
            return False

        try:
            repo.head.reset(commit_hash, index=True, working_tree=True)
            return True
        except Exception:
            return False
