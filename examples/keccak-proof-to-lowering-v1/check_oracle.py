#!/usr/bin/env python3
"""Check dmir-dump.txt against expected-oracle.json (Section 5.3 running example)."""
import json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
oracle = json.loads((HERE / "expected-oracle.json").read_text())
dump = (HERE / "dmir-dump.txt").read_text()
sections = {}
for case in ("covered", "uncovered"):
    marker = f"######## KECCAK offset {oracle[case]['keccak_offset']} ########"
    start = dump.index(marker) + len(marker)
    nxt = dump.find("######## KECCAK offset", start)
    sections[case] = dump[start:] if nxt < 0 else dump[start:nxt]

ok = True
for case, text in sections.items():
    spec = oracle[case]
    checks = [(f"calls <{spec['expect_helper']}>", f"<{spec['expect_helper']}>" in text),
              (f"never calls <{spec['forbid_helper']}>", f"<{spec['forbid_helper']}>" not in text)]
    checks += [(f"contains '{line}'", line in text) for line in spec["expect_lines"]]
    for name, passed in checks:
        print(f"{'PASS' if passed else 'FAIL'}  {case} ({spec['keccak_offset']}): {name}")
        ok &= passed
sys.exit(0 if ok else 1)
