// Standalone driver: compile the paper's running example (Fig. 1 program) with
// the same frontend path as EVMMirBuilderMemoryProofTest and print the dMIR.
// Built against a DTVM 338d123-based build with STACK_SSA_LIFT=ON and
// MEMORY_PLAN_FRAMEWORK=ON.
#include "compiler/evm_frontend/evm_imported.h"
#include "compiler/evm_frontend/evm_mir_compiler.h"
#include "compiler/mir/module.h"
#include "llvm/Support/raw_ostream.h"
#include <evmc/instructions.h>

#include <array>
#include <cstdint>
#include <cstdio>
#include <optional>
#include <string>
#include <vector>

static std::optional<std::string>
compileMir(const std::vector<uint8_t> &Bytecode) {
  COMPILER::EVMFrontendContext Ctx;
  Ctx.setRevision(EVMC_CANCUN);
  Ctx.setBytecode(reinterpret_cast<const zen::common::Byte *>(Bytecode.data()),
                  Bytecode.size());

  COMPILER::MModule Mod(Ctx);
  std::array<COMPILER::MType *, 1> ParamTypes = {
      COMPILER::MPointerType::create(Ctx, Ctx.VoidType)};
  COMPILER::MFunctionType *FuncType = COMPILER::MFunctionType::create(
      Ctx, Ctx.VoidType, llvm::ArrayRef<COMPILER::MType *>(ParamTypes));
  Mod.addFuncType(FuncType);

  COMPILER::MFunction Func(Ctx, 0);
  Func.setFunctionType(FuncType);
  COMPILER::EVMMirBuilder Builder(Ctx, Func);
  if (!Builder.compile(&Ctx)) {
    return std::nullopt;
  }

  std::string Mir;
  llvm::raw_string_ostream OS(Mir);
  Func.print(OS);
  OS.flush();
  return Mir;
}

// Fig. 1 program.  Block layout: B0 @0x00, B2 @0x12 (fallthrough), B1 @0x1e,
// B3 @0x28.  `Off` is the KECCAK offset pushed on both predecessor paths
// (0x40 = covered by the recovered extent 0x60; 0x60 = not covered).
static std::vector<uint8_t> fig1Program(uint8_t Off) {
  return {
      // B0: x <- CALLDATALOAD(0) & (2^64-1); cond <- ISZERO(x); JUMPI B1
      OP_PUSH1, 0x00, OP_CALLDATALOAD,
      OP_PUSH8, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, OP_AND,
      OP_DUP1, OP_ISZERO, OP_PUSH1, 0x1e, OP_JUMPI,
      // B2 @0x12: CALLDATACOPY(0x40, 0x00, 0x20); off <- Off; JUMP B3
      OP_PUSH1, 0x20, OP_PUSH1, 0x00, OP_PUSH1, 0x40, OP_CALLDATACOPY,
      OP_PUSH1, Off, OP_PUSH1, 0x28, OP_JUMP,
      // B1 @0x1e: MSTORE(0x40, x); off <- Off; JUMP B3
      OP_JUMPDEST, OP_DUP1, OP_PUSH1, 0x40, OP_MSTORE,
      OP_PUSH1, Off, OP_PUSH1, 0x28, OP_JUMP,
      // B3 @0x28: small <- LT(x, 0x20); m <- MSIZE; h <- KECCAK256(off, 0x20)
      OP_JUMPDEST, OP_PUSH1, 0x20, OP_DUP3, OP_LT, OP_MSIZE,
      OP_PUSH1, 0x20, OP_DUP4, OP_KECCAK256, OP_STOP};
}

int main() {
  const auto &RT = COMPILER::getRuntimeFunctionTable();
  std::printf("# runtime helper addresses\n");
  std::printf("GetKeccak256         = %llu\n",
              (unsigned long long)COMPILER::getFunctionAddress(RT.GetKeccak256));
  std::printf("GetKeccak256NoExpand = %llu\n",
              (unsigned long long)COMPILER::getFunctionAddress(
                  RT.GetKeccak256NoExpand));

  for (uint8_t Off : {uint8_t(0x40), uint8_t(0x60)}) {
    const auto Code = fig1Program(Off);
    std::printf("\n# ===== bytecode (KECCAK offset 0x%02x, %zu bytes) =====\n", Off,
                Code.size());
    for (uint8_t B : Code) std::printf("%02x", B);
    std::printf("\n");
    const auto Mir = compileMir(Code);
    if (!Mir) {
      std::printf("compile FAILED\n");
      continue;
    }
    std::printf("# ----- dMIR -----\n%s\n", Mir->c_str());
  }
  return 0;
}
