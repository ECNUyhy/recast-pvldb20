# Independent KEVM cross-check

This package cross-checks the prepared memory paths used by ReCAST against
KEVM's executable semantics. Each pair runs the same opcode on empty memory and
on memory pre-expanded to cover the same range, and checks identical output
bytes.

## Result

`results.json` records seven passing executions: the KEVM package smoke test
(`tests/interactive/add.json` from the KEVM release) and the ordinary and
pre-expanded forms of `CALLDATACOPY`, `CODECOPY`, and `KECCAK256`.

## Reproduction

Install the KEVM release pinned in `version-lock.json`, then run:

```bash
bash scripts/run-fixtures.sh
```

The runner executes the six copy/hash fixtures with the Cancun schedule. Set
`KEVM_BIN` if the executable is not named `kevm`.

## Scope

Each pair compares output bytes. Pre-expansion consumes gas, so gas left is not
compared. Compiler-side properties (fact propagation, helper selection, and
fallback) are covered by the test suites summarized in Table 3 of the paper.
