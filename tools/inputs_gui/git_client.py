# ==============================================================================
# [FILE]    git_client.py
# [PROJECT] my_TV_Movie
# [ROLE]    Small git helpers for GUI (status / pull-rebase / commit+push)
# [VERSION] v0.1.0
# [UPDATED] 2026-02-24
# ==============================================================================

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Tuple


class GitClient:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def _run(self, args: list[str]) -> Tuple[bool, str]:
        try:
            p = subprocess.run(
                ["git", *args],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
            out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
            return (p.returncode == 0), out.strip()
        except Exception as ex:
            return False, str(ex)

    def status_short(self) -> Tuple[bool, str]:
        return self._run(["status", "--porcelain=v1", "--branch"])

    def pull_rebase_main(self) -> Tuple[bool, str]:
        ok1, out1 = self._run(["fetch", "origin"])
        if not ok1:
            return False, out1
        ok2, out2 = self._run(["rebase", "origin/main"])
        return ok2, (out2 or out1)

    def commit_and_push_inputs(self, message: str, inputs_rel: str) -> Tuple[bool, str]:
        ok1, out1 = self._run(["add", inputs_rel])
        if not ok1:
            return False, out1
        ok2, out2 = self._run(["commit", "-m", message])
        if not ok2:
            return False, out2
        ok3, out3 = self._run(["push"])
        return ok3, out3
