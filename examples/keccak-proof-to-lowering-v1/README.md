# KECCAK proof-to-lowering running example

This directory binds the paper's running example (Figure 1; Figures 3-5 follow
it through Recover, Admit, and Specialize) to the compiler's generated dMIR at
source commit `338d123a5d9d4a464d8d0151158447d500a9997a`, built with Stack SSA and the memory-plan framework enabled.

The two bytecodes (51 bytes each) differ only in the KECCAK offset pushed on
both predecessor paths (bytes 0x1a and 0x24). `B1` executes `MSTORE(0x40, x)`
and `B2` executes `CALLDATACOPY(0x40, 0, 0x20)`, so both establish logical
memory through `0x60` before the merge at `B3` (pc `0x28`), where
`LT(x, 0x20)`, `MSIZE`, and `KECCAK256(off, 0x20)` follow. The covered case
(`off = 0x40`) hashes `[0x40, 0x60)` and must select `GetKeccak256NoExpand`;
the fallback case (`off = 0x60`) hashes `[0x60, 0x80)` and must retain the
generic `GetKeccak256` helper. In both cases `x` is merged by an ordered phi
(`$41 = phi [...]`), `LT` lowers to a single 64-bit compare
(`cmp iult ($41, const.i64 32)`), and the `MSIZE` read (`$46 = $5`) stays in
place; only the KECCAK call differs.

`dmir-dump.txt` is the compiler's dMIR for both bytecodes, produced by
`mir-dump-driver.cpp` (a standalone driver over the same frontend path as the
directed test `EVMMirBuilderMemoryProofTest`). Because runtime helper addresses
change from run to run, the file omits the driver's address table, replaces the
two KECCAK helper addresses by their names from that table, and heads each case
with a `######## KECCAK offset ... ########` marker; the dMIR is otherwise the
driver's output. `expected-oracle.json` lists,
per case, the helper that must be called, the helper that must not appear,
and the lines that must be present. Figure 5 abridges this dump: helper
addresses are shown by name and the instance pointer as `inst`.

This is a source-bound executable oracle, not a timing workload. Run
`python3 check_oracle.py` to check `dmir-dump.txt` against `expected-oracle.json`.
