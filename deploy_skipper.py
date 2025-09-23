#!/usr/bin/env python3
"""
deploy_skipper.py
──────────────────────────────────────────────────────────────────────────────
A tiny, zero-dependency utility that tells your CI/CD pipeline whether to
deploy or skip, based on blacklist + whitelist patterns in `.deployignore`.

Usage
─────
  # Diff against previous commit
  $ ./deploy_skipper.py

  # Diff against most recent tag
  $ ./deploy_skipper.py --tag

  # Diff against specific commit
  $ ./deploy_skipper.py --ref 3f4e2a1

  # Verbose output
  $ ./deploy_skipper.py --verbose

Exit codes
──────────
  0  – proceed with deployment (changes detected)
  1  – skip deployment (only ignored files changed)
  2  – misconfiguration / error

.deployignore format
───────────────────
# Lines starting with "!" are whitelist (un-ignore)
!path/to/keep.txt

# Other patterns are blacklist (ignore)
*.png
build/*
src/**
"""
import subprocess
import argparse
import sys
from pathlib import Path, PurePosixPath
from fnmatch import fnmatch
from typing import List, Tuple, Optional

DEFAULT_IGNORE_FILE = ".deployignore"


def load_patterns(ignore_file: Path) -> Tuple[List[str], List[str]]:
    """
    Parse the ignore file and return (blacklist_patterns, whitelist_patterns).
    - Lines starting with '!' are whitelist patterns (un-ignore).
    - Other non-empty, non-comment lines are blacklist patterns (ignore).
    Normalizes leading './' in patterns.
    """
    if not ignore_file.exists():
        print(f"ERROR: {ignore_file} not found.", file=sys.stderr)
        sys.exit(2)

    blacklist: List[str] = []
    whitelist: List[str] = []

    for raw in ignore_file.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue

        if line.startswith("!"):
            pat = line[1:].lstrip()
            if pat.startswith("./"):
                pat = pat[2:]
            if pat:
                whitelist.append(pat)
        else:
            pat = line
            if pat.startswith("./"):
                pat = pat[2:]
            if pat:
                blacklist.append(pat)

    return blacklist, whitelist


def normalize_path(p: str) -> str:
    """Remove leading './' if present (git diffs usually don't include it)."""
    return p[2:] if p.startswith("./") else p


def matches_dir_star(file_path: str, pattern: str) -> bool:
    """
    Special-case pattern that ends with '/*': match files under the dir
    and the directory itself. e.g. pattern 'src/*' should match 'src', 'src/a.py', etc.
    """
    if not pattern.endswith("/*"):
        return False
    dir_prefix = pattern[:-2]
    return file_path == dir_prefix or file_path.startswith(dir_prefix + "/")


def posix_match(path: str, pattern: str) -> bool:
    """
    Use PurePosixPath.match to support '**' recursive globs and other glob features.
    Fall back to fnmatch for patterns that are more naturally handled that way.
    We use PurePosixPath.match because it understands '**' semantics.
    """
    # Use PurePosixPath, ensure we're using POSIX-style separators
    p = PurePosixPath(path)
    # PurePosixPath.match expects patterns like 'src/**/a.py' or '*.md'
    try:
        if p.match(pattern):
            return True
    except Exception:
        # If pattern is something unexpected, fall back to fnmatch
        pass

    # fnmatch still useful for some patterns; normalized path is posix-like already
    return fnmatch(path, pattern)


def path_matches_any(path: str, patterns: List[str]) -> Optional[str]:
    """
    Return the first matching pattern if path matches any glob pattern in patterns.
    Uses posix_match (with ** support) and also honors the special 'dir/*' rule.
    Returns the matching pattern string or None if no match.
    """
    for p in patterns:
        # special-case trailing '/*' to include the directory itself
        if matches_dir_star(path, p):
            return p
        if posix_match(path, p):
            return p
    return None


def is_ignored(file_path: str, blacklist: List[str], whitelist: List[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Determine whether file_path should be ignored.
    Returns a tuple (ignored: bool, matched_pattern: Optional[str], matched_kind: Optional['blacklist'|'whitelist']).
    Semantics:
    - If it matches any whitelist pattern => NOT ignored (whitelist wins).
    - Else if it matches any blacklist pattern => ignored.
    - Else => NOT ignored.
    """
    path = normalize_path(file_path)

    # Check whitelist first (whitelist always wins)
    wl_match = path_matches_any(path, whitelist) if whitelist else None
    if wl_match:
        return False, wl_match, "whitelist"

    bl_match = path_matches_any(path, blacklist) if blacklist else None
    if bl_match:
        return True, bl_match, "blacklist"

    return False, None, None


def changed_files(ref: str) -> List[str]:
    """Return a list of changed files compared to `ref` (compares ref to HEAD)."""
    try:
        cmd = ["git", "diff", "--name-only", ref, "HEAD"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return [line for line in result.stdout.splitlines() if line.strip()]
    except subprocess.CalledProcessError as e:
        print(f"ERROR: git diff failed: {e}", file=sys.stderr)
        sys.exit(2)


def latest_tag() -> str:
    """Return the most recent tag or exit with error."""
    try:
        cmd = ["git", "describe", "--tags", "--abbrev=0"]
        tag = subprocess.check_output(cmd, text=True).strip()
        return tag
    except subprocess.CalledProcessError:
        print("ERROR: No tags found.", file=sys.stderr)
        sys.exit(2)


def main() -> None:  # pragma: nocover
    parser = argparse.ArgumentParser(
        description="Determine if deployment is necessary based on .deployignore"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--ref",
        help="Git ref/commit to diff against (default: HEAD~1)",
    )
    group.add_argument(
        "--tag",
        action="store_true",
        help="Diff against the most recent tag",
    )
    parser.add_argument(
        "--ignore-file",
        default=DEFAULT_IGNORE_FILE,
        help=f"Path to whitelist/blacklist file (default: {DEFAULT_IGNORE_FILE})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print loaded patterns and matching information for each changed file",
    )
    args = parser.parse_args()

    ignore_file = Path(args.ignore_file)
    blacklist, whitelist = load_patterns(ignore_file)

    if not blacklist and not whitelist:
        print("ERROR: No patterns found in .deployignore.", file=sys.stderr)
        sys.exit(2)

    if args.verbose:
        print("Loaded patterns:")
        if blacklist:
            print("  Blacklist (ignore) patterns:")
            for p in blacklist:
                print(f"    {p}")
        else:
            print("  Blacklist: (none)")

        if whitelist:
            print("  Whitelist (un-ignore) patterns:")
            for p in whitelist:
                print(f"    {p}")
        else:
            print("  Whitelist: (none)")
        print()

    if args.tag:
        ref = latest_tag()
    else:
        ref = args.ref or "HEAD~1"

    changes = changed_files(ref)
    if not changes:
        print("No changes detected; skipping deployment.")
        sys.exit(1)

    relevant_changes: List[str] = []
    for f in changes:
        ignored, matched_pattern, matched_kind = is_ignored(f, blacklist, whitelist)
        if args.verbose:
            if matched_pattern:
                print(f"{f}: matched {matched_kind} pattern '{matched_pattern}' -> {'IGNORED' if ignored else 'RELEVANT'}")
            else:
                print(f"{f}: no matching pattern -> RELEVANT")

        if not ignored:
            relevant_changes.append(f)

    if relevant_changes:
        print("Relevant changes detected, proceeding with deployment:")
        for f in relevant_changes:
            print(f"  {f}")
        sys.exit(0)
    else:
        print("All changes are ignored by blacklist/whitelist rules; skipping deployment.")
        sys.exit(1)


if __name__ == "__main__":
    main()
