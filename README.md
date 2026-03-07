# ice40-template

Amaranth HDL project template for Lattice iCE40 FPGAs with SystemVerilog integration,
Verilator simulation, SymbiYosys formal verification, and a fully reproducible Nix-based
toolchain.

## Overview

The design uses [Amaranth HDL](https://amaranth-lang.org/) to generate a Verilog top-level
that instantiates hand-written SystemVerilog modules from `rtl/`. The example design is a
24-bit counter driving an LED, verified through simulation, formal proofs, and Python unit
tests before synthesis.

```
Amaranth (Python)          SystemVerilog
ice40_template/top.py  -->  build/gen/top.v  --+--> Verilator (sim)
                                               |
rtl/counter.sv  -------------------------------+--> SymbiYosys (formal)
                                               |
                                               +--> Yosys -> nextpnr -> icestorm (FPGA)
```

## Supported boards

| Board | Device | Package | Clock |
|-------|--------|---------|-------|
| `ice40_hx8k_evn` (default) | iCE40HX8K | CT256 | 12 MHz |
| `icebreaker` | iCE40UP5K | SG48 | 12 MHz |
| `icestick` | iCE40HX1K | TQ144 | 12 MHz |

Board definitions live in `data/config/config.cue`. Run `task boards` to list them.

## Prerequisites

[Nix](https://nixos.org/download) with flakes enabled. Everything else is provided by
the flake.

## Setup

```sh
git clone <repo-url> && cd ice40-template
nix develop
```

The dev shell provides all tools (Verilator, Yosys, nextpnr, icestorm, SymbiYosys, z3,
Verible, Ruff, uv, go-task, GTKWave, CUE) and auto-syncs the Python virtualenv on first
entry.

Install the pre-commit hooks:

```sh
pre-commit install
```

## Quick start

```sh
task sim                        # generate Verilog + run Verilator simulation
task formal                     # generate Verilog + run formal verification
task build                      # synthesize, place & route, generate bitstream
task program                    # program the FPGA via iceprog
```

## Task reference

All commands are run through [Task](https://taskfile.dev/).

### Build & program

| Command | Description |
|---------|-------------|
| `task build` | Synth + P&R + bitstream (default board) |
| `task build BOARD=icebreaker` | Build for a specific board |
| `task program` | Flash bitstream with iceprog |
| `task verilog` | Generate Verilog from Amaranth only |
| `task boards` | List available boards |

### Simulation

| Command | Description |
|---------|-------------|
| `task sim` | Run Verilator simulation (generates Verilog first) |
| `task sim TB=tb_top` | Run a specific testbench |
| `task waves` | Open the latest VCD in GTKWave |
| `task waves VCD=build/sim/tb_top.vcd` | Open a specific VCD |

### Verification & testing

| Command | Description |
|---------|-------------|
| `task formal` | Run SymbiYosys formal verification (prove + cover) |
| `task test` | Run Python unit tests via Nox (Python 3.10-3.12) |
| `task typecheck` | Type-check `ice40_template/` with ty |

### Linting & formatting

| Command | Description |
|---------|-------------|
| `task format` | Auto-format Python (Ruff) |
| `task format-check` | Check Python formatting (CI mode) |
| `task lint` | Lint + auto-fix Python (Ruff) |
| `task lint-check` | Lint Python without fixing (CI mode) |
| `task format-verilog` | Auto-format Verilog/SystemVerilog (Verible) |
| `task format-verilog-check` | Check Verilog formatting (CI mode) |
| `task lint-verilog` | Lint Verilog/SystemVerilog (Verible) |
| `task lint-rtl` | Lint RTL with Verilator (`-Wall`) |
| `task lint-gen` | Lint generated Verilog + RTL together |

### Aggregate

| Command | Description |
|---------|-------------|
| `task check` | Run all checks (typecheck, lint, test, formal, sim) |
| `task clean` | Remove all build artifacts |

## Project structure

```
ice40_template/          Amaranth Python package
  __init__.py              sv_sources() entry point for RTL discovery
  top.py                   Top-level Amaranth design

rtl/                     Hand-written SystemVerilog
  counter.sv               Parameterized counter with formal assertions

testbenches/             Verilator C++ testbenches
  tb_top.cpp               SystemC testbench for the top-level design

tests/                   Python unit tests
  test_top.py              Amaranth elaboration test

scripts/                 Build orchestration (Python)
  build.py                 FPGA build + Verilog generation
  sim.py                   Verilator simulation runner
  formal.py                SymbiYosys formal verification runner
  common.py                Shared utilities (logging, SV source collection)

data/config/
  config.cue               Board and build configuration (CUE)

.github/workflows/
  ci.yml                   GitHub Actions CI pipeline
```

Build artifacts go to `build/` (gitignored):

```
build/
  gen/top.v              Generated Verilog from Amaranth
  fpga/{board}/top.bin   FPGA bitstream
  sim/{tb}.vcd           Simulation waveforms
  formal/top.sby         Generated SymbiYosys config
  logs/                  Build/sim/formal logs
```

## Development workflow

1. Modify the Amaranth design in `ice40_template/top.py` or SystemVerilog in `rtl/`.
2. Run `task sim` to simulate -- this generates Verilog and runs Verilator automatically.
3. Run `task formal` to formally verify RTL assertions.
4. Run `task test` for Python unit tests.
5. Run `task check` to run the full suite before pushing.
6. Commit -- pre-commit hooks enforce the same checks CI runs.
7. Run `task build` and `task program` to deploy to hardware.

### Adding a new SystemVerilog module

1. Add the `.sv` file to `rtl/`.
2. Instantiate it from Amaranth using `m.submodules += Instance(...)` in `top.py`.
3. Add formal assertions inside `ifdef FORMAL` blocks.
4. Add a Verilator testbench in `testbenches/` if needed.

### Adding a new board

Add an entry to `data/config/config.cue` with the `amaranth_boards` platform class path
and device info, then build with `task build BOARD=<name>`.

## CI pipeline

GitHub Actions runs on every push to `main` and on pull requests. The pipeline mirrors
the local `task check` workflow:

```
[Parallel lint jobs]
  format-check, format-verilog-check, lint, lint-verilog, lint-rtl, typecheck
        |
    lint-gen  (generated Verilog + RTL)
        |
      test  (Python unit tests via Nox)
       / \
     sim   formal
      \   /
      build  (push to main only)
```

Pre-commit hooks run the same `-check` commands as CI, so if pre-commit passes locally,
CI will pass too.

## Toolchain summary

| Tool | Purpose |
|------|---------|
| [Amaranth HDL](https://amaranth-lang.org/) | Hardware description (Python to Verilog) |
| [Yosys](https://yosyshq.net/yosys/) | Synthesis |
| [nextpnr](https://github.com/YosysHQ/nextpnr) | Place & route |
| [Project IceStorm](https://clifford.at/icestorm/) | Bitstream generation + programming |
| [Verilator](https://www.veripool.org/verilator/) | Simulation + RTL linting |
| [SymbiYosys](https://symbiyosys.readthedocs.io/) + z3 | Formal verification |
| [Verible](https://chipsalliance.github.io/verible/) | Verilog formatting + linting |
| [Ruff](https://docs.astral.sh/ruff/) | Python formatting + linting |
| [ty](https://github.com/astral-sh/ty) | Python type checking |
| [Nox](https://nox.thea.codes/) | Python test sessions |
| [uv](https://docs.astral.sh/uv/) | Python package management |
| [Task](https://taskfile.dev/) | Task runner |
| [CUE](https://cuelang.org/) | Configuration |
| [Nix](https://nixos.org/) | Reproducible dev environment |
