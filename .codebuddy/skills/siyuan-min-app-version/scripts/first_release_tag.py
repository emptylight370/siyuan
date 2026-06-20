#!/usr/bin/env python3
"""Given commits, print the earliest formal release tag containing each.

Usage:
    python first_release_tag.py <repo_path> <commit> [commit2 ...]

Filters tags to formal releases (^v\\d+(\\.\\d+)*$), sorts them by semver
numeric comparison (not lexicographic), and prints the earliest one per
commit. Exits non-zero if a commit is not contained in any formal release.
"""

import re
import subprocess
import sys

TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def run_git(repo: str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def tag_key(tag: str):
    match = TAG_RE.match(tag)
    return tuple(int(part) for part in match.groups())


def earliest_release_tag(repo: str, commit: str) -> str | None:
    output = run_git(repo, "tag", "--contains", commit)
    tags = [line.strip() for line in output.splitlines() if line.strip()]
    releases = sorted((t for t in tags if TAG_RE.match(t)), key=tag_key)
    return releases[0] if releases else None


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    repo, commits = sys.argv[1], sys.argv[2:]
    status = 0
    for commit in commits:
        try:
            tag = earliest_release_tag(repo, commit)
        except RuntimeError as exc:
            print(f"{commit}: ERROR {exc}")
            status = 1
            continue
        if tag:
            print(f"{commit} -> {tag}")
        else:
            print(f"{commit} -> (not contained in any formal release tag)")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())
