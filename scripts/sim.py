#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


def generate_verilog() -> bool:
    print("Generating Verilog from Amaranth...")
    result = subprocess.run(
        ["uv", "run", "python", "scripts/build.py", "--verilog-only"],
        capture_output=False,
    )
    return result.returncode == 0


def run_verilator(testbench: str, top_module: str = "tb_top") -> bool:
    build_dir = Path("build/sim")
    build_dir.mkdir(parents=True, exist_ok=True)

    gen_verilog = Path("build/gen/top.v")
    rtl_files = list(Path("rtl").glob("*.sv"))
    tb_file = Path(f"testbenches/{testbench}.sv")

    if not gen_verilog.exists():
        print("✗ Generated Verilog not found. Run verilog generation first.")
        return False

    if not tb_file.exists():
        print(f"✗ Testbench {tb_file} not found")
        return False

    print(f"\nRunning Verilator simulation: {testbench}")
    print(f"  Testbench: {tb_file}")
    print(f"  RTL files: {len(rtl_files)} SystemVerilog files")

    verilator_cmd = [
        "verilator",
        "--binary",
        "--trace",
        "-Wall",
        "-Wno-fatal",
        "--top-module",
        top_module,
        "-Mdir",
        str(build_dir / "obj_dir"),
        str(tb_file),
        str(gen_verilog),
        *[str(f) for f in rtl_files],
    ]

    try:
        result = subprocess.run(verilator_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"✗ Verilator failed:\n{result.stderr}")
            return False

        print("✓ Verilator compilation successful")

        sim_exe = build_dir / "obj_dir" / f"V{top_module}"
        if not sim_exe.exists():
            print(f"✗ Simulation executable not found: {sim_exe}")
            return False

        print("\nRunning simulation...")
        result = subprocess.run([str(sim_exe)], capture_output=True, text=True)

        if result.returncode == 0:
            print("✓ Simulation completed")
            print(result.stdout)

            vcd_file = build_dir / f"{testbench}.vcd"
            if vcd_file.exists():
                print(f"  VCD: {vcd_file}")
            return True
        else:
            print(f"✗ Simulation failed:\n{result.stderr}")
            return False

    except FileNotFoundError:
        print("✗ Verilator not found. Install via Nix: nix develop")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Verilator simulation")
    parser.add_argument("--testbench", "-t", default="tb_top", help="Testbench name")
    parser.add_argument("--skip-gen", action="store_true", help="Skip Verilog generation")

    args = parser.parse_args()

    if not args.skip_gen and not generate_verilog():
        return 1

    success = run_verilator(args.testbench)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
