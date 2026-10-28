#!/usr/bin/env python3
"""Generate the 99 Experiment 5 ablation programs.

Each program chains basic blocks with unconditional jumps and varies the
consumer family, the chain length, and a semantic shape (a, b, c).
Generation reads no timing data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


OP = {
    "STOP": 0x00,
    "ADD": 0x01,
    "MUL": 0x02,
    "SUB": 0x03,
    "DIV": 0x04,
    "MOD": 0x06,
    "AND": 0x16,
    "XOR": 0x18,
    "KECCAK256": 0x20,
    "CALLDATALOAD": 0x35,
    "POP": 0x50,
    "MLOAD": 0x51,
    "MSTORE": 0x52,
    "JUMP": 0x56,
    "JUMPI": 0x57,
    "GAS": 0x5A,
    "JUMPDEST": 0x5B,
    "MCOPY": 0x5E,
    "DUP1": 0x80,
    "SWAP1": 0x90,
    "RETURN": 0xF3,
    "STATICCALL": 0xFA,
}

PROVENANCE = {
    "repository": "https://github.com/DTVMStack/evmone",
    "commit": "a4a0e47aff903a47a6be133c67ad106c706fe566",
    "memory_seed": {
        "path": "test/unittests/evm_benchmark_test.cpp",
        "sha256": "7a091d277b875e08d27396c6b5d1cd51ff96240dbf92f0bfdbc30ffcf6f4039b",
        "kernel": "grow_memory_with_mload/grow_memory_with_mstore",
    },
    "arithmetic_stack_seed": {
        "path": "test/bench/synthetic_benchmarks.cpp",
        "sha256": "809ee2cd1345a7b376d91f86b3c39e38c54d2ba8b2ea822913372b2b852417d6",
        "kernel": "generate_loop_v2/generate_loop_inner_code",
    },
}


class Assembler:
    def __init__(self) -> None:
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[int, str]] = []

    def op(self, name: str) -> None:
        self.code.append(OP[name])

    def push(self, value: int, width: int | None = None) -> None:
        if value < 0:
            raise ValueError("negative PUSH value")
        if width is None:
            width = max(1, (value.bit_length() + 7) // 8)
        if not 1 <= width <= 32 or value >= 1 << (8 * width):
            raise ValueError("PUSH value does not fit")
        self.code.append(0x5F + width)
        self.code.extend(value.to_bytes(width, "big"))

    def dup(self, depth: int) -> None:
        if not 1 <= depth <= 16:
            raise ValueError("DUP depth out of range")
        self.code.append(0x7F + depth)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"duplicate label: {name}")
        self.labels[name] = len(self.code)
        self.op("JUMPDEST")

    def jump(self, label: str, conditional: bool = False) -> None:
        self.code.append(0x61)
        self.fixups.append((len(self.code), label))
        self.code.extend(b"\x00\x00")
        self.op("JUMPI" if conditional else "JUMP")

    def finish(self) -> bytes:
        for offset, label in self.fixups:
            if label not in self.labels:
                raise ValueError(f"unknown label: {label}")
            target = self.labels[label]
            if target >= 1 << 16:
                raise ValueError("candidate exceeds PUSH2 address space")
            self.code[offset : offset + 2] = target.to_bytes(2, "big")
        return bytes(self.code)




GENERATOR_VERSION = "exp5-formal-candidate-v2"
DENSITY_SITES = {"low": 2, "medium": 8, "high": 32}
SHAPES = ("a", "b", "c")


@dataclass(frozen=True)
class Spec:
    domain: str
    family: str
    density: str
    shape: str

    @property
    def case_id(self) -> str:
        return f"{self.domain}-{self.family}-{self.density}-{self.shape}"


def raw(a: Assembler, opcode: int) -> None:
    a.code.append(opcode)


def emit_return(a: Assembler, offset: int = 0) -> None:
    a.push(0x20)
    a.push(offset)
    raw(a, 0xF3)


def emit_memory_consumer(a: Assembler, family: str, shape: str) -> None:
    shape_index = SHAPES.index(shape)
    offset = 0x80 + shape_index * 0x20
    if family == "mcopy":
        a.push(0x20)
        a.push(0x100)
        a.push(offset)
        raw(a, 0x5E)
    elif family == "external_copy":
        a.push(0x20)
        a.push(shape_index * 4)
        a.push(offset)
        raw(a, 0x37 if shape != "c" else 0x39)
    elif family == "keccak":
        a.push(0x20)
        a.push(offset)
        raw(a, 0x20)
        raw(a, 0x50)
    elif family == "call_io":
        a.push(0x20)
        a.push(0x40 + shape_index * 0x20)
        a.push(0x20)
        a.push(offset)
        a.push(0)
        raw(a, 0x5A)
        raw(a, 0xFA)
        raw(a, 0x50)
    else:
        raise ValueError(f"unknown repeatable memory family: {family}")


def generate_memory(spec: Spec) -> bytes:
    sites = DENSITY_SITES[spec.density]
    shape_index = SHAPES.index(spec.shape)
    a = Assembler()
    a.push(shape_index + 1)
    a.push(0x200)
    raw(a, 0x52)
    a.jump("m0")

    if spec.family == "return_revert":
        for index in range(sites):
            a.label(f"m{index}")
            if index + 1 < sites:
                a.push(shape_index + index + 1)
                raw(a, 0x50)
                a.jump(f"m{index + 1}")
        a.push(0x20)
        a.push(0x80 + shape_index * 0x20)
        raw(a, 0xFD if spec.shape == "b" else 0xF3)
        return a.finish()

    for index in range(sites):
        a.label(f"m{index}")
        emit_memory_consumer(a, spec.family, spec.shape)
        if index + 1 < sites:
            a.jump(f"m{index + 1}")
    emit_return(a)
    return a.finish()


def arithmetic_opcode(family: str, shape: str) -> int:
    shape_index = SHAPES.index(shape)
    return {
        "add_sub": (0x01, 0x03, 0x01),
        "mul": (0x02, 0x02, 0x02),
        "div_mod": (0x04, 0x06, 0x04),
    }[family][shape_index]


def generate_u256(spec: Spec) -> bytes:
    sites = DENSITY_SITES[spec.density]
    opcode = arithmetic_opcode(spec.family, spec.shape)
    a = Assembler()
    raw(a, 0x5A)
    a.jump("u0")
    for index in range(sites):
        a.label(f"u{index}")
        raw(a, 0x5A)
        raw(a, opcode)
        if index + 1 < sites:
            a.jump(f"u{index + 1}")
    a.push(0)
    raw(a, 0x52)
    emit_return(a)
    return a.finish()


STACK_LIVE_VALUES = {"live1": 1, "live2": 2, "live4": 4}


def generate_stack(spec: Spec) -> bytes:
    sites = DENSITY_SITES[spec.density]
    live = STACK_LIVE_VALUES[spec.family]
    shape_index = SHAPES.index(spec.shape)
    a = Assembler()
    for index in range(live):
        a.push(index * 0x20)
        raw(a, 0x35)
    a.jump("s0")
    for index in range(sites):
        a.label(f"s{index}")
        if live == 1:
            a.push(shape_index + 1)
            raw(a, 0x18)
        else:
            a.dup(live)
            raw(a, 0x18)
        if index + 1 < sites:
            a.jump(f"s{index + 1}")
    for _ in range(live - 1):
        raw(a, 0x18)
    a.push(0)
    raw(a, 0x52)
    emit_return(a)
    return a.finish()


def iter_specs() -> Iterable[Spec]:
    domains = {
        "memory": ("mcopy", "external_copy", "keccak", "call_io", "return_revert"),
        "u256": ("add_sub", "mul", "div_mod"),
        "stack": tuple(STACK_LIVE_VALUES),
    }
    for domain, families in domains.items():
        for family in families:
            for density in DENSITY_SITES:
                for shape in SHAPES:
                    yield Spec(domain, family, density, shape)


def generate_bytecode(spec: Spec) -> bytes:
    if spec.domain == "memory":
        return generate_memory(spec)
    if spec.domain == "u256":
        return generate_u256(spec)
    return generate_stack(spec)


def generate(output_root: Path) -> list[dict]:
    fixture_root = output_root / "fixtures" / "formal-candidates-v2"
    manifest_root = output_root / "manifests"
    fixture_root.mkdir(parents=True, exist_ok=True)
    manifest_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for spec in iter_specs():
        bytecode = generate_bytecode(spec)
        calldata = hashlib.sha256(("exp5-v2:" + spec.case_id).encode()).digest()
        sites = DENSITY_SITES[spec.density]
        seed = PROVENANCE[
            "memory_seed" if spec.domain == "memory" else "arithmetic_stack_seed"
        ]
        row = {
            "schema_version": 2,
            "generator_version": GENERATOR_VERSION,
            "candidate_id": spec.case_id,
            "cell_id": spec.case_id,
            "domain": spec.domain,
            "family": spec.family,
            "density": spec.density,
            "shape": spec.shape,
            "proof_distance_blocks": sites,
            "target_dynamic_activations": 1 if spec.family == "return_revert" else sites,
            "bytecode_file": f"fixtures/formal-candidates-v2/{spec.case_id}.hex",
            "bytecode_bytes": len(bytecode),
            "bytecode_sha256": hashlib.sha256(bytecode).hexdigest(),
            "calldata_hex": calldata.hex(),
            "calldata_sha256": hashlib.sha256(calldata).hexdigest(),
            "evm_revision": "cancun",
            "gas_limit": 1_000_000_000,
            "public_seed": seed,
            "expected": None,
        }
        (output_root / row["bytecode_file"]).write_text(bytecode.hex() + "\n")
        rows.append(row)

    manifest = manifest_root / "formal-candidate-pool-v2.jsonl"
    manifest.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    provenance = {
        "schema_version": 2,
        "generator_version": GENERATOR_VERSION,
        "candidate_count": len(rows),
        "domain_counts": {
            domain: sum(row["domain"] == domain for row in rows)
            for domain in ("memory", "u256", "stack")
        },
        "selection_uses_timing": False,
        "public_provenance": PROVENANCE,
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
    }
    (manifest_root / "formal-candidate-pool-v2.provenance.json").write_text(
        json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    rows = generate(args.output_root)
    print(json.dumps({"generated": len(rows)}, sort_keys=True))
    return 0 if len(rows) == 99 else 1


if __name__ == "__main__":
    raise SystemExit(main())
