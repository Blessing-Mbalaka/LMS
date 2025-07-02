#!/usr/bin/env python3
"""
add_ids.py  – injects a unique "id" into every dict node of a JSON exam spec

Usage
-----
$ python add_ids.py exam.json             # prints JSON-with-ids to stdout
$ python add_ids.py exam.json -o new.json # writes to new.json in-place
"""

import json, uuid, argparse, sys, pathlib

def ensure_ids(node):
    """Recursively add an 'id' key (UUID4) to every dict that doesn’t have one."""
    if isinstance(node, dict):
        node.setdefault("id", uuid.uuid4().hex)     # 32-char hex
        for v in node.values():
            ensure_ids(v)
    elif isinstance(node, list):
        for v in node:
            ensure_ids(v)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("src", help="input JSON file")
    p.add_argument("-o", "--out", help="write result here (defaults to stdout)")
    args = p.parse_args()

    data = json.loads(pathlib.Path(args.src).read_text(encoding="utf-8"))
    ensure_ids(data)
    dumped = json.dumps(data, indent=2, ensure_ascii=False)

    if args.out:
        pathlib.Path(args.out).write_text(dumped, encoding="utf-8")
    else:
        sys.stdout.write(dumped)

if __name__ == "__main__":
    main()
