#!/usr/bin/env python3
"""Rejoin systemd directives whose continuation was written without a
trailing backslash.  Idempotent; prints a diff and touches nothing else."""
import difflib
import pathlib
import sys

for path in map(pathlib.Path, sys.argv[1:]):
    lines = path.read_text().splitlines()
    out, i = [], 0
    while i < len(lines):
        cur = lines[i]
        if ("=" in cur and not cur.startswith((" ", "\t", "#", "["))
                and i + 1 < len(lines)
                and lines[i + 1].startswith(("  ", "\t"))
                and "=" not in lines[i + 1]
                and lines[i + 1].strip()):
            out.append(cur.rstrip() + " " + lines[i + 1].strip())
            i += 2
            continue
        out.append(cur)
        i += 1
    new = "\n".join(out) + "\n"
    if new != path.read_text():
        sys.stdout.writelines(difflib.unified_diff(
            path.read_text().splitlines(True), new.splitlines(True),
            str(path), str(path) + " (fixed)"))
        path.write_text(new)
