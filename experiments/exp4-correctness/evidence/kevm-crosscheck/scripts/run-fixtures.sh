#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
kevm_bin=${KEVM_BIN:-kevm}

"$kevm_bin" version

for fixture in \
  calldatacopy-generic.evm \
  calldatacopy-preexpanded.evm \
  codecopy-generic.evm \
  codecopy-preexpanded.evm \
  keccak-generic.evm \
  keccak-preexpanded.evm
do
  "$kevm_bin" run "$root/fixtures/$fixture" \
    --schedule CANCUN --mode VMTESTS
done
