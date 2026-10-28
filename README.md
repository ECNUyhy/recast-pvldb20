# ReCAST artifact

Data and scripts behind the figures and tables of *ReCAST: Effect-Constrained
JIT Specialization for Replicated EVM Transaction Processing* (PVLDB Vol. 20).
ReCAST is implemented in the public [DTVM repository](https://github.com/DTVMStack/DTVM);
the paper system is commit `338d123`.

## Paper results

| Paper item | Data | Script |
|---|---|---|
| Table 2, opportunity census | `experiments/exp3-mainnet-replay/evidence/opportunity-census/FAST-PATH-RESULTS.tsv` | tabular |
| Section 4.3, recovery budgets | `experiments/exp3-mainnet-replay/evidence/budget-sensitivity-v1/` | tabular |
| Figure 6, cold compilation | `experiments/exp1-cold-compilation/evidence/{cross-engine,same-source-ablation}/` | `render_exp1_single_column.py` |
| Section 7.1, reth breakdown | `experiments/reth-breakdown/reth-breakdown-summary.csv` | tabular |
| Figures 7 and 8, steady-state and online execution | `experiments/exp2-performance/evidence/**/analysis/`, workloads in `**/cases/` | `figure-generation/render_composites.py` |
| Figure 9, mainnet replay | `experiments/exp3-mainnet-replay/evidence/exp3-mainnet-replay.tsv` | `generate-exp3-mainnet-replay.py` |
| Figure 10, ablation | `experiments/exp5-cross-block-ablation/evidence/analysis/formal-v1/`, programs in `fixtures/` | `analysis/render_ablation_figure.py` |
| Table 3, correctness | `experiments/exp4-correctness/evidence/` (KEVM cross-check in `kevm-crosscheck/`) | tabular |
| Figures 1 and 3–5, Section 5.3, running example | `examples/keccak-proof-to-lowering-v1/` | `check_oracle.py` |

Names in data: in Experiment 1, `dtvm_*` fields are ReCAST, and `V111`/`V000` are
full ReCAST and ReCAST-disabled; in Experiment 5, `ReCAST core disabled` is the
DTVM baseline.

## Setup

The pinned versions in `requirements.txt` need Python 3.10 or 3.11 (numpy 1.24.2
has no wheels for Python 3.12 or newer). With Python 3.11 installed:

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
```

Otherwise, [uv](https://docs.astral.sh/uv/) fetches Python 3.11 without root access:

```bash
uv venv --python 3.11 .venv && . .venv/bin/activate
uv pip install -r requirements.txt
```

## Commands

Run from the repository root.

```bash
# Figure 6
python experiments/exp1-cold-compilation/evidence/render_exp1_single_column.py \
  --root experiments/exp1-cold-compilation/evidence --output-dir reproduced/exp1

# Figures 7 and 8 (Figure 8 arranges the four exp2-online-*-panel outputs 2x2)
python experiments/exp2-performance/evidence/figure-generation/render_composites.py \
  --root experiments/exp2-performance/evidence --output-dir reproduced/exp2

# Figure 9 (writes next to the script, so run it on a copy)
mkdir -p reproduced/exp3
cp experiments/exp3-mainnet-replay/evidence/exp3-mainnet-replay.tsv \
   experiments/exp3-mainnet-replay/evidence/generate-exp3-mainnet-replay.py reproduced/exp3/
python reproduced/exp3/generate-exp3-mainnet-replay.py

# Figure 10
python experiments/exp5-cross-block-ablation/evidence/analysis/render_ablation_figure.py \
  --summary experiments/exp5-cross-block-ablation/evidence/analysis/formal-v1/formal-summary.json \
  --output-dir reproduced/exp5 --provenance reproduced/exp5/PROVENANCE.json

# Section 5.3 running example
python examples/keccak-proof-to-lowering-v1/check_oracle.py

# KEVM cross-check (requires the KEVM release in version-lock.json)
bash experiments/exp4-correctness/evidence/kevm-crosscheck/scripts/run-fixtures.sh
```

Figure typography can differ slightly across Matplotlib versions; plotted
values are fixed by the released data.

## Host, toolchains, and forks

- Host: single-socket Intel Xeon Gold 6330 (28 cores, 56 hardware threads),
  123 GiB of memory, Ubuntu 26.04 LTS. The Section 7.1 reth breakdown ran on a
  separate reth node: Intel Core Ultra 7 265KF, 46 GiB of memory, and the
  database on a Samsung 990 PRO NVMe SSD.
- Builds: binary hashes in `provenance/implementation-identity.json`.
- Workloads: the five evm-bench contracts are compiled with solc 0.8.30 or
  0.4.26 (version and flags in the system-comparison `cases-manifest.json`);
  the other workloads are public evm-benchmarks fixtures, identified by hash in
  their `cases-manifest.json`. The ablation programs are listed in
  `experiments/exp5-cross-block-ablation/evidence/manifests/formal-99-v2.jsonl`.
- Forks: microbenchmarks, the ablation, and the running example use Cancun;
  the state tests cover Frontier through Osaka; mainnet blocks are replayed
  under their mainnet fork rules.

## License

Apache License 2.0, as upstream DTVM. See `LICENSE`.
