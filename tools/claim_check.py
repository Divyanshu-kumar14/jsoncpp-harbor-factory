#!/usr/bin/env python3
# Vendored from the submission-integrity skill for CI; keep behavior identical.
"""Fail-closed claim check: every number in prose must exist in an evidence file.

  python tools/claim_check.py --prose README.md docs/demo_script.md \
                              --evidence reports/ bench/ eval/ \
                              --allow tools/claim_allow.txt

Exit 0 = every number traced. Exit 1 = unverified claims (BLOCK). Exit 2 = no evidence.
"""
import argparse
import re
import sys
from pathlib import Path

NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
SKIP = re.compile(r"^\s*(#|```|\||!\[|http|<!--)")
YEAR = re.compile(r"^(19|20)\d{2}$")
PROSE_EXT = {".md", ".txt", ".srt", ".vtt"}
NL = chr(10)


def numbers(text):
    return {m.group().replace(",", "") for m in NUM.finditer(text)}


def expand(paths, exts=None):
    files = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files += [f for f in p.rglob("*")
                      if f.is_file() and (exts is None or f.suffix in exts)]
        else:
            print("MISSING PATH: " + raw)
            sys.exit(2)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prose", nargs="+", required=True)
    ap.add_argument("--evidence", nargs="+", required=True)
    ap.add_argument("--allow", default=None)
    a = ap.parse_args()

    ev_files = expand(a.evidence)
    evidence = set()
    for f in ev_files:
        evidence |= numbers(f.read_text(errors="ignore"))
    if not evidence:
        print("NO EVIDENCE FOUND. Nothing can be verified. BLOCK.")
        return 2

    if a.allow:
        for line in Path(a.allow).read_text().splitlines():
            body, _, reason = line.partition("#")
            if body.strip() and not reason.strip():
                print("ALLOWLIST ENTRY WITHOUT A SOURCE: " + line)
                return 2
            evidence |= numbers(body)

    bad = []
    for f in expand(a.prose, PROSE_EXT):
        for lineno, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            if SKIP.match(line):
                continue
            for m in NUM.finditer(line):
                n = m.group().replace(",", "")
                if YEAR.match(n) or n in evidence:
                    continue
                bad.append((str(f), lineno, m.group(), line.strip()[:88]))

    for path, lineno, n, ctx in bad:
        print("UNVERIFIED  " + path + ":" + str(lineno) + "  number=" + n)
        print("            " + ctx)

    print(NL + str(len(bad)) + " unverified number(s); "
          + str(len(ev_files)) + " evidence file(s) scanned.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
